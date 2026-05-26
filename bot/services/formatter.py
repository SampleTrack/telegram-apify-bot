from config import MIN_DISCOUNT_PERCENT


# ── Deal Scoring ──────────────────────────────────────────

def score_deal(product: dict) -> float:
    """
    Score a product as a deal (higher = better).
    Formula: discount% (50%) + rating (30%) + review popularity (20%)
    Max possible score = 100.
    """
    discount = min(product.get("discount", 0), 80)   # cap at 80%
    discount_score = (discount / 80) * 50             # 0–50 pts

    try:
        rating = float(str(product.get("rating", 0)).split("/")[0])
    except (ValueError, TypeError):
        rating = 0
    rating_score = (rating / 5) * 30                  # 0–30 pts

    try:
        reviews = int(str(product.get("reviews", 0)).replace(",", ""))
    except (ValueError, TypeError):
        reviews = 0
    # log scale: 1 review=0, 100=13.8, 1000=23, 10000=32.8 → cap at 20
    import math
    review_score = min(math.log1p(reviews) / math.log1p(10000) * 20, 20)

    return round(discount_score + rating_score + review_score, 1)


def deal_badge(score: float) -> str:
    if score >= 75:
        return "🔥🔥 MEGA DEAL"
    if score >= 55:
        return "🔥 HOT DEAL"
    if score >= 35:
        return "✅ GOOD DEAL"
    return "💡 DEAL"


def product_card(product: dict, index: int = None) -> str:
    """Format a single product as a Telegram message card."""
    discount = product.get("discount", 0)
    price = product.get("price", 0)
    original = product.get("original_price", 0)
    rating = product.get("rating", "N/A")
    reviews = product.get("reviews", 0)
    title = product.get("title", "Unknown Product")
    url = product.get("url", "")
    asin = product.get("asin", "")

    # Discount badge
    badge = ""
    if discount >= 30:
        badge = "🔥 HOT DEAL"
    elif discount >= MIN_DISCOUNT_PERCENT:
        badge = "✅ DEAL"

    prefix = f"**{index}.** " if index else ""

    lines = [f"{prefix}🛒 **{title}**\n"]

    if badge:
        lines.append(f"{badge} — **{discount}% OFF**")

    if original > price:
        lines.append(f"💰 ~~₹{original:,.0f}~~ → **₹{price:,.0f}**")
    else:
        lines.append(f"💰 **₹{price:,.0f}**")

    if rating != "N/A":
        stars = "⭐" * min(int(float(str(rating))), 5) if str(rating).replace(".", "").isdigit() else "⭐"
        lines.append(f"{stars} {rating}/5  ({reviews:,} reviews)")

    if url:
        lines.append(f"[🔗 View on Amazon]({url})")

    if asin:
        lines.append(f"`ASIN: {asin}`")

    return "\n".join(lines)


def search_results_message(keyword: str, products: list[dict]) -> str:
    """Format multiple products as a search result message."""
    if not products:
        return f"😕 No results found for **{keyword}**.\n\nTry a different keyword."

    header = f"🔍 **Amazon Results: {keyword}**\n{'─' * 30}\n\n"
    cards = []
    for i, p in enumerate(products, 1):
        cards.append(product_card(p, index=i))

    return header + "\n\n".join(cards)


def deal_channel_post(keyword: str, products: list[dict]) -> str:
    """
    Format a rich deals post for your Telegram channel.
    Products are already sorted by score (best first).
    """
    if not products:
        return ""

    top = products[0]
    top_score = score_deal(top)
    badge = deal_badge(top_score)

    lines = [
        f"{badge}",
        f"🛍️ **Amazon Deals — {keyword.title()}**",
        f"{'─' * 28}\n",
    ]

    for i, p in enumerate(products[:5], 1):
        discount = p.get("discount", 0)
        title = p.get("title", "")[:65]
        price = p.get("price", 0)
        original = p.get("original_price", 0)
        rating = p.get("rating", "")
        url = p.get("url", "")
        sc = score_deal(p)

        discount_tag = f"**{discount}% OFF**" if discount else ""
        rating_tag = f"⭐{rating}" if rating and rating != "N/A" else ""

        lines.append(f"**{i}. {title}**")
        if original > price:
            lines.append(f"   💰 ~~₹{original:,.0f}~~ → **₹{price:,.0f}**  {discount_tag}")
        else:
            lines.append(f"   💰 **₹{price:,.0f}**")

        meta = "   "
        if rating_tag:
            meta += f"{rating_tag}  "
        meta += f"📊 Score: {sc}/100"
        lines.append(meta)

        if url:
            lines.append(f"   [🔗 Buy Now]({url})\n")

    lines.append("💬 _Forward to someone who'd love this deal!_")
    return "\n".join(lines)


def best_deals_summary(all_products: list[dict], top_n: int = 3) -> str:
    """
    Pick the absolute best N deals across all keywords and format
    as a single 'Best of the Day' channel post.
    """
    if not all_products:
        return ""

    scored = sorted(all_products, key=score_deal, reverse=True)
    top = scored[:top_n]

    lines = [
        "🏆 **Best Amazon Deals Right Now**",
        f"{'─' * 30}\n",
    ]

    for i, p in enumerate(top, 1):
        sc = score_deal(p)
        badge = deal_badge(sc)
        title = p.get("title", "")[:65]
        price = p.get("price", 0)
        original = p.get("original_price", 0)
        discount = p.get("discount", 0)
        rating = p.get("rating", "")
        url = p.get("url", "")

        lines.append(f"{badge}  #{i}")
        lines.append(f"📦 **{title}**")
        if original > price:
            lines.append(f"💰 ~~₹{original:,.0f}~~ → **₹{price:,.0f}**  ({discount}% off)")
        else:
            lines.append(f"💰 **₹{price:,.0f}**")
        if rating and rating != "N/A":
            lines.append(f"⭐ {rating}/5  |  Score: {sc}/100")
        if url:
            lines.append(f"[🛒 Grab it here]({url})\n")

    lines.append("📲 _Share this with your friends!_")
    return "\n".join(lines)


def price_drop_alert(product: dict, old_price: float, new_price: float) -> str:
    """Alert message for a price drop on a tracked product."""
    drop = old_price - new_price
    drop_pct = round((drop / old_price) * 100) if old_price > 0 else 0
    title = product.get("title", "Your tracked product")
    url = product.get("url", "")

    return (
        f"🚨 **Price Drop Alert!**\n\n"
        f"📦 {title}\n\n"
        f"💸 ~~₹{old_price:,.0f}~~ → **₹{new_price:,.0f}**\n"
        f"📉 Dropped by ₹{drop:,.0f} ({drop_pct}% off)\n\n"
        f"[🔗 Buy Now]({url})"
    )
