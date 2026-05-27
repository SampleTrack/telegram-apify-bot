import logging
import httpx
from config import APIFY_TOKEN

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
HEADERS = {"Authorization": f"Bearer {APIFY_TOKEN}"}


async def get_account_info() -> dict | None:
    """Fetch Apify account info including plan and usage."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{APIFY_BASE}/users/me", headers=HEADERS)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            logger.error(f"Apify account info error: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"get_account_info exception: {e}")
    return None


async def get_recent_runs(limit: int = 10) -> list[dict]:
    """Fetch recent Actor runs."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{APIFY_BASE}/actor-runs",
                headers=HEADERS,
                params={"limit": limit, "desc": True},
            )
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("items", [])
            logger.error(f"Apify runs error: {resp.status_code}")
    except Exception as e:
        logger.error(f"get_recent_runs exception: {e}")
    return []


async def get_usage_stats() -> dict:
    """
    Return a unified usage summary dict with:
    - plan name, monthly credit limit, used credits
    - remaining credits + percentage used
    - recent run count and statuses
    """
    info = await get_account_info()
    runs = await get_recent_runs(limit=20)

    stats = {
        "username": "N/A",
        "plan": "N/A",
        "monthly_limit_usd": 5.0,       # Free plan default
        "used_usd": 0.0,
        "remaining_usd": 5.0,
        "usage_pct": 0.0,
        "total_runs": 0,
        "succeeded": 0,
        "failed": 0,
        "running": 0,
        "proxy_groups": [],
        "recent_runs": [],
    }

    if info:
        stats["username"] = info.get("username") or info.get("id", "N/A")

        # Plan details
        plan = info.get("plan") or {}
        stats["plan"] = plan.get("id") or plan.get("name") or "FREE"
        stats["monthly_limit_usd"] = float(
            plan.get("monthlyUsageCreditsUsd") or
            plan.get("monthlyUsdBudget") or 5.0
        )

        # Usage details (Apify returns usage inside the user object)
        usage = (
            info.get("monthlyUsage") or
            info.get("usage") or
            info.get("stats") or {}
        )
        stats["used_usd"] = float(
            usage.get("totalUsd") or
            usage.get("usedUsd") or
            usage.get("monthlyUsageUsd") or 0.0
        )

        limit = stats["monthly_limit_usd"]
        used = stats["used_usd"]
        stats["remaining_usd"] = max(0.0, round(limit - used, 4))
        stats["usage_pct"] = round((used / limit * 100) if limit > 0 else 0, 1)

    # Run statistics
    if runs:
        stats["total_runs"] = len(runs)
        stats["succeeded"] = sum(1 for r in runs if r.get("status") == "SUCCEEDED")
        stats["failed"] = sum(1 for r in runs if r.get("status") in ("FAILED", "ABORTED", "TIMED-OUT"))
        stats["running"] = sum(1 for r in runs if r.get("status") == "RUNNING")

        # Format recent runs for display
        from datetime import datetime
        for r in runs[:5]:
            started = r.get("startedAt", "")
            try:
                dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                time_str = dt.strftime("%d %b %H:%M")
            except Exception:
                time_str = started[:16] if started else "—"

            stats["recent_runs"].append({
                "actor": r.get("actorId", "unknown")[-20:],
                "status": r.get("status", "UNKNOWN"),
                "usage_usd": round(float(r.get("usageTotalUsd") or r.get("stats", {}).get("totalUsd") or 0), 4),
                "time": time_str,
            })

    return stats


def format_usage_message(stats: dict) -> str:
    """Format usage stats as a Telegram message."""
    used = stats["used_usd"]
    limit = stats["monthly_limit_usd"]
    remaining = stats["remaining_usd"]
    pct = stats["usage_pct"]

    # Progress bar (10 blocks)
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Usage colour indicator
    if pct >= 90:
        status_icon = "🔴"
    elif pct >= 60:
        status_icon = "🟡"
    else:
        status_icon = "🟢"

    lines = [
        "📊 **Apify Usage Dashboard**",
        f"👤 Account: `{stats['username']}`",
        f"📦 Plan: **{stats['plan']}**",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "💳 **Monthly Credits**",
        f"{status_icon} `{bar}` {pct}%",
        f"   Used:      **${used:.4f}**",
        f"   Remaining: **${remaining:.4f}**",
        f"   Limit:     **${limit:.2f} / month**",
        "",
        "🏃 **Recent Runs (last 20)**",
        f"   ✅ Succeeded : {stats['succeeded']}",
        f"   ❌ Failed    : {stats['failed']}",
        f"   ⏳ Running   : {stats['running']}",
    ]

    if stats["recent_runs"]:
        lines.append("")
        lines.append("🕐 **Last 5 Runs**")
        status_icons = {
            "SUCCEEDED": "✅",
            "FAILED": "❌",
            "ABORTED": "⛔",
            "TIMED-OUT": "⏰",
            "RUNNING": "⏳",
        }
        for r in stats["recent_runs"]:
            icon = status_icons.get(r["status"], "❓")
            lines.append(
                f"   {icon} `{r['actor']}` — ${r['usage_usd']:.4f} — {r['time']}"
            )

    # Warning if close to limit
    if pct >= 90:
        lines += ["", "⚠️ **WARNING: Almost out of credits!**", "_Upgrade plan or reduce scraping frequency_"]
    elif pct >= 70:
        lines += ["", "💡 _Tip: Reduce MAX\\_RESULTS or increase CACHE\\_TTL to save credits_"]

    return "\n".join(lines)
