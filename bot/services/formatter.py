from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _now() -> datetime:
    return datetime.now(IST)


def _stars(rating) -> str:
    try:
        n = min(round(float(str(rating).split("/")[0])), 5)
        return "⭐" * n
    except Exception:
        return "⭐"


def _badge(discount: int) -> str:
    if discount >= 50: return "🔥🔥 MEGA DEAL"
    if discount >= 30: return "🔥 HOT DEAL"
    if discount >= 15: return "✅ GOOD DEAL"
    return "💡 DEAL"


def _score(p: dict) -> float:
    """Simple deal score: discount (50%) + rating (30%) + reviews (20%)."""
    import math
    d = min(p.get("discount", 0), 80)
    try: r = float(str(p.get("rating", 0)).split("/")[0])
    except: r = 0
    try: rv = int(str(p.get("reviews", 0)).replace(",", ""))
    except: rv = 0
    return (d/80)*50 + (r/5)*30 + min(math.log1p(rv)/math.log1p(10000)*20, 20)


# ── Product card ──────────────────────────────────────────

def _card(p: dict, rank: int = None) -> str:
    title    = p.get("title", "")[:70]
    price    = p.get("price", 0)
    original = p.get("original", 0)
    discount = p.get("discount", 0)
    rating   = p.get("rating", "N/A")
    reviews  = p.get("reviews", 0)
    url      = p.get("url", "")

    lines = []
    if rank:
        lines.append(f"**#{rank} — {_badge(discount)}**")
    else:
        lines.append(f"**{_badge(discount)}**")

    lines.append(f"📦 {title}")

    if original > price:
        lines.append(f"💰 ~~₹{original:,.0f}~~ → **₹{price:,.0f}**")
        lines.append(f"📉 Save **₹{original-price:,.0f}** ({discount}% off)")
    else:
        lines.append(f"💰 **₹{price:,.0f}**")

    if rating != "N/A":
        try:
            rv = int(str(reviews).replace(",",""))
            lines.append(f"{_stars(rating)} {rating}/5  ({rv:,} reviews)")
        except Exception:
            lines.append(f"{_stars(rating)} {rating}/5")

    if url:
        lines.append(f"[🛒 Buy on Amazon]({url})")

    return "\n".join(lines)


# ── Morning post ──────────────────────────────────────────

def morning_post(keyword: str, products: list[dict]) -> str:
    if not products:
        return ""
    date = _now().strftime("%d %B %Y")
    top  = sorted(products, key=_score, reverse=True)[:4]

    lines = [
        f"🌅 **Good Morning! Amazon Deals**",
        f"📅 {date}  •  🔎 {keyword.title()}",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for i, p in enumerate(top, 1):
        lines.append(_card(p, rank=i))
        lines.append("\n" + ("─" * 24) + "\n")

    lines.append("💬 _Forward to save your friends money!_")
    lines.append("🔔 _Turn on notifications for daily deals!_")
    return "\n".join(lines)


# ── Evening summary ───────────────────────────────────────

def evening_post(all_products: list[dict]) -> str:
    if not all_products:
        return ""
    top   = sorted(all_products, key=_score, reverse=True)[:3]
    date  = _now().strftime("%d %B")

    medals = ["🥇", "🥈", "🥉"]
    lines  = [
        f"🌙 **Best Deals of the Day — {date}**",
        "🏆 Top 3 picks from today",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for i, p in enumerate(top):
        title    = p.get("title","")[:65]
        price    = p.get("price", 0)
        original = p.get("original", 0)
        discount = p.get("discount", 0)
        url      = p.get("url","")

        lines.append(f"{medals[i]} **{title}**")
        if original > price:
            lines.append(f"   💰 ~~₹{original:,.0f}~~ → **₹{price:,.0f}** ({discount}% off)")
        else:
            lines.append(f"   💰 **₹{price:,.0f}**")
        if url:
            lines.append(f"   [Buy Now]({url})")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📲 _Share with your squad!_ 👇",
    ]
    return "\n".join(lines)


# ── Flash sale alert ──────────────────────────────────────

def flash_post(products: list[dict]) -> str:
    hot = [p for p in products if p.get("discount", 0) >= 40]
    if not hot:
        return ""
    hot = sorted(hot, key=_score, reverse=True)[:3]

    lines = [
        "⚡ **FLASH SALE ALERT!** ⚡",
        f"🔥 {len(hot)} products with **40%+ OFF** right now!",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for p in hot:
        title    = p.get("title","")[:65]
        price    = p.get("price", 0)
        original = p.get("original", 0)
        discount = p.get("discount", 0)
        url      = p.get("url","")

        lines.append(f"🔴 **{title}**")
        lines.append(f"   ~~₹{original:,.0f}~~ → **₹{price:,.0f}** 🔥 **{discount}% OFF**")
        if url:
            lines.append(f"   [⚡ Grab it!]({url})")
        lines.append("")

    lines += ["⏰ _Limited time — act now!_", "📲 _Tag a friend who needs this!_"]
    return "\n".join(lines)
