import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID, MAX_RESULTS, MIN_DISCOUNT_PERCENT
from bot.services.apify import search_amazon, parse_product, get_deals
from bot.services.cache import cache_get, cache_set, make_key
from bot.services.formatter import search_results_message, product_card
from bot.db.mongo import (
    add_tracked_product,
    get_user_tracked,
    remove_tracked_product,
    log_search,
)

logger = logging.getLogger(__name__)


def register_handlers(app: Client):
    """Register all message handlers on the Pyrogram client."""

    # ── /start ────────────────────────────────────────────
    @app.on_message(filters.command("start") & filters.private)
    async def start_cmd(client: Client, message: Message):
        name = message.from_user.first_name or "there"
        await message.reply(
            f"👋 Hey **{name}**!\n\n"
            "I'm your **Amazon Deal Hunter Bot** powered by Apify 🕷️\n\n"
            "**Commands:**\n"
            "🔍 `/search <keyword>` — Search Amazon products\n"
            "📉 `/deals <keyword>` — Find discounted products\n"
            "📌 `/track <ASIN>` — Track price of a product\n"
            "📋 `/mylist` — View your tracked products\n"
            "❌ `/untrack <ASIN>` — Stop tracking a product\n"
            "❓ `/help` — Show this menu\n\n"
            "_Powered by Apify + Pyrogram_"
        )

    # ── /help ─────────────────────────────────────────────
    @app.on_message(filters.command("help"))
    async def help_cmd(client: Client, message: Message):
        await message.reply(
            "📖 **Bot Help**\n\n"
            "`/search iphone 13` — Search Amazon\n"
            "`/deals earbuds` — Get deals with discounts\n"
            "`/track B09G9HD6PD` — Track product by ASIN\n"
            "`/mylist` — See all tracked products\n"
            "`/untrack B09G9HD6PD` — Remove from tracking\n\n"
            "💡 **Tip:** Deals are cached for 1 hour to save credits!"
        )

    # ── /search ───────────────────────────────────────────
    @app.on_message(filters.command("search"))
    async def search_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("❗ Usage: `/search <keyword>`\n\nExample: `/search iphone 13 case`")
            return

        keyword = args[1].strip()
        status_msg = await message.reply(f"🔍 Searching Amazon for **{keyword}**...\n_This may take 15–30 seconds_")

        # Check cache first
        cache_key = make_key("amazon_search", keyword)
        cached = await cache_get(cache_key)

        if cached:
            products = cached
            await status_msg.edit("✅ Results (from cache):")
        else:
            raw_items = await search_amazon(keyword, MAX_RESULTS)
            products = [p for p in (parse_product(r) for r in raw_items) if p]

            if products:
                await cache_set(cache_key, products)

        await log_search(message.from_user.id, keyword, len(products))

        if not products:
            await status_msg.edit(f"😕 No results found for **{keyword}**. Try a different keyword.")
            return

        result_text = search_results_message(keyword, products)
        await status_msg.edit(result_text, disable_web_page_preview=True)

    # ── /deals ────────────────────────────────────────────
    @app.on_message(filters.command("deals"))
    async def deals_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "❗ Usage: `/deals <keyword>`\n\n"
                "Example: `/deals bluetooth earbuds`\n"
                f"_Shows products with {MIN_DISCOUNT_PERCENT}%+ discount_"
            )
            return

        keyword = args[1].strip()
        status_msg = await message.reply(f"🔥 Hunting deals for **{keyword}**...")

        cache_key = make_key("amazon_deals", keyword)
        products = await cache_get(cache_key)

        if not products:
            products = await get_deals(keyword, MIN_DISCOUNT_PERCENT)
            if products:
                await cache_set(cache_key, products)

        if not products:
            await status_msg.edit(
                f"😕 No deals found for **{keyword}** with {MIN_DISCOUNT_PERCENT}%+ discount.\n\n"
                "Try `/search` instead to see all products."
            )
            return

        result_text = search_results_message(f"{keyword} (deals)", products)
        await status_msg.edit(result_text, disable_web_page_preview=True)

    # ── /track ────────────────────────────────────────────
    @app.on_message(filters.command("track"))
    async def track_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "❗ Usage: `/track <ASIN>`\n\n"
                "ASIN is the product code from Amazon URL.\n"
                "Example: `/track B09G9HD6PD`"
            )
            return

        asin = args[1].strip().upper()
        status_msg = await message.reply(f"📌 Looking up ASIN **{asin}** on Amazon...")

        # Search for product by ASIN
        cache_key = make_key("amazon_search", asin)
        products = await cache_get(cache_key)

        if not products:
            raw_items = await search_amazon(asin, 1)
            products = [p for p in (parse_product(r) for r in raw_items) if p]
            if products:
                await cache_set(cache_key, products)

        if not products:
            await status_msg.edit(
                f"❌ Could not find product with ASIN **{asin}**.\n"
                "Make sure the ASIN is correct."
            )
            return

        product = products[0]
        product["asin"] = asin

        saved = await add_tracked_product(message.from_user.id, product)
        if saved:
            await status_msg.edit(
                f"✅ **Now tracking!**\n\n"
                f"{product_card(product)}\n\n"
                f"🔔 You'll get an alert when the price drops!"
            )
        else:
            await status_msg.edit("❌ Failed to save. Please try again.")

    # ── /mylist ───────────────────────────────────────────
    @app.on_message(filters.command("mylist"))
    async def mylist_cmd(client: Client, message: Message):
        tracked = await get_user_tracked(message.from_user.id)

        if not tracked:
            await message.reply(
                "📋 Your tracking list is empty.\n\n"
                "Use `/track <ASIN>` to start tracking products!"
            )
            return

        lines = ["📋 **Your Tracked Products:**\n"]
        for i, item in enumerate(tracked, 1):
            lines.append(
                f"{i}. **{item['title'][:50]}**\n"
                f"   💰 ₹{item['last_price']:,.0f}  |  `{item['asin']}`\n"
                f"   [View]({item['url']})"
            )

        lines.append(f"\n_Use `/untrack <ASIN>` to remove a product_")
        await message.reply("\n".join(lines), disable_web_page_preview=True)

    # ── /untrack ──────────────────────────────────────────
    @app.on_message(filters.command("untrack"))
    async def untrack_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("❗ Usage: `/untrack <ASIN>`")
            return

        asin = args[1].strip().upper()
        removed = await remove_tracked_product(message.from_user.id, asin)

        if removed:
            await message.reply(f"✅ Removed **{asin}** from your tracking list.")
        else:
            await message.reply(f"❌ **{asin}** not found in your list.")

    # ── Admin: /broadcast ─────────────────────────────────
    @app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
    async def broadcast_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("❗ Usage: `/broadcast <message>`")
            return
        from bot.scheduler.jobs import post_deals_to_channel
        await message.reply("📢 Posting deals to channel...")
        await post_deals_to_channel(client)
        await message.reply("✅ Done!")

    # ── Admin: /postdeals ─────────────────────────────────
    @app.on_message(filters.command("postdeals") & filters.user(OWNER_ID))
    async def postdeals_cmd(client: Client, message: Message):
        """Manually trigger best deals post to channel right now."""
        args = message.text.split(maxsplit=1)

        status = await message.reply("🔍 Finding best deals...")

        if len(args) >= 2:
            # Post deals for a specific keyword
            keyword = args[1].strip()
            from bot.services.apify import get_deals
            from bot.services.formatter import deal_channel_post, score_deal
            from bot.db.mongo import is_deal_posted, mark_deal_posted
            from config import MIN_DISCOUNT_PERCENT

            products = await get_deals(keyword, MIN_DISCOUNT_PERCENT)
            fresh = [
                p for p in products
                if p.get("asin") and not await is_deal_posted(p["asin"], hours=48)
            ]
            fresh.sort(key=score_deal, reverse=True)

            if not fresh:
                await status.edit(f"😕 No new deals for **{keyword}** right now.")
                return

            text = deal_channel_post(keyword, fresh)
            await client.send_message(CHANNEL_ID, text, disable_web_page_preview=False)
            for p in fresh[:5]:
                await mark_deal_posted(p.get("asin",""), p.get("title",""), p.get("price",0), p.get("discount",0))
            await status.edit(f"✅ Posted {len(fresh[:5])} deals for **{keyword}** to channel!")

        else:
            # Post deals for all default keywords
            from bot.scheduler.jobs import post_deals_to_channel
            await post_deals_to_channel(client)
            await status.edit("✅ Best deals posted to channel!")

    # ── Admin: /recentdeals ───────────────────────────────
    @app.on_message(filters.command("recentdeals") & filters.user(OWNER_ID))
    async def recentdeals_cmd(client: Client, message: Message):
        """Show last 10 deals posted to the channel."""
        from bot.db.mongo import get_recent_posted_deals
        deals = await get_recent_posted_deals(limit=10)

        if not deals:
            await message.reply("📭 No deals posted yet.")
            return

        lines = ["📋 **Recently Posted Deals:**\n"]
        for i, d in enumerate(deals, 1):
            posted = d.get("posted_at")
            time_str = posted.strftime("%d %b %H:%M") if posted else "—"
            lines.append(
                f"{i}. **{d.get('title','?')[:50]}**\n"
                f"   ₹{d.get('price',0):,.0f}  |  {d.get('discount',0)}% off  |  {time_str}"
            )
        await message.reply("\n".join(lines))

    # ── Admin: /stats ─────────────────────────────────────
    @app.on_message(filters.command("stats") & filters.user(OWNER_ID))
    async def stats_cmd(client: Client, message: Message):
        from bot.db.mongo import get_db
        db = get_db()
        tracked_count = await db["tracked_products"].count_documents({})
        search_count = await db["search_history"].count_documents({})
        posted_count = await db["posted_deals"].count_documents({})
        await message.reply(
            f"📊 **Bot Stats**\n\n"
            f"📌 Tracked products: **{tracked_count}**\n"
            f"🔍 Total searches: **{search_count}**\n"
            f"📢 Deals posted: **{posted_count}**"
        )

    # ── Admin: /apifyusage ────────────────────────────────
    @app.on_message(filters.command("apifyusage") & filters.user(OWNER_ID))
    async def apify_usage_cmd(client: Client, message: Message):
        """Show Apify account usage, credits remaining, and recent runs."""
        status = await message.reply("⏳ Fetching Apify usage...")
        from bot.services.apify_stats import get_usage_stats, format_usage_message
        stats = await get_usage_stats()
        text = format_usage_message(stats)
        await status.edit(text)

    logger.info("All handlers registered ✅")
