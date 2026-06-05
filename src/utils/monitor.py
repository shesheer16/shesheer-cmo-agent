"""
src/utils/monitor.py
Monitoring utilities — weekly Telegram report + KB health check.
No email dependency (uses Telegram only for simplicity).
"""
import os
from datetime import datetime, timedelta
from loguru import logger


def get_weekly_stats() -> dict:
    """Pulls stats from SQLite for the last 7 days."""
    stats = {
        "conversations": 0,
        "total_cost_inr": 0.0,
        "total_tokens": 0,
        "top_model": "N/A",
        "errors": 0,
    }
    try:
        from src.memory.database import SessionLocal
        from src.memory.models import Conversation, CostTracker
        from sqlalchemy import func

        db = SessionLocal()
        week_ago = datetime.utcnow() - timedelta(days=7)

        # Conversation count
        conv_count = db.query(Conversation).filter(
            Conversation.created_at >= week_ago
        ).count()
        stats["conversations"] = conv_count

        # Cost this week
        cost_rows = db.query(
            func.sum(CostTracker.cost_inr),
            func.sum(CostTracker.tokens_used),
            CostTracker.model
        ).filter(
            CostTracker.date >= week_ago.date()
        ).group_by(CostTracker.model).all()

        for row in cost_rows:
            stats["total_cost_inr"] += float(row[0] or 0)
            stats["total_tokens"] += int(row[1] or 0)
            stats["top_model"] = row[2] or "N/A"

        db.close()
    except Exception as e:
        logger.error(f"Weekly stats query failed: {e}")

    return stats


def get_kb_health() -> dict:
    """Checks ChromaDB chunk counts across all collections."""
    health = {"total_chunks": 0, "status": "ok"}
    try:
        from src.knowledge.chroma_client import get_collection
        collections = [
            "founders_mindsets", "campaign_case_studies", "cmo_profiles",
            "market_data_reports", "consumer_psychology", "books_annotations",
            "social_intelligence"
        ]
        for col_name in collections:
            try:
                health["total_chunks"] += get_collection(col_name).count()
            except Exception:
                pass

        if health["total_chunks"] < 100:
            health["status"] = "warning: low chunk count"
    except Exception as e:
        health["status"] = f"error: {e}"

    return health


def generate_weekly_report() -> str:
    """Generates the weekly Telegram report message."""
    stats = get_weekly_stats()
    kb = get_kb_health()
    now = datetime.now().strftime("%d %b %Y")

    report = f"""📊 *Weekly CMO Agent Report — {now}*

💬 *Conversations this week:* {stats['conversations']}
🪙 *Total cost this week:* ₹{stats['total_cost_inr']:.2f}
📦 *Tokens used:* {stats['total_tokens']:,}
🤖 *Model:* {stats['top_model']}

🧠 *Knowledge Base:*
• Chunks in ChromaDB: {kb['total_chunks']}
• Status: {kb['status']}

⚡ *System:* Running on Render free tier
📅 *Next report:* {(datetime.now() + timedelta(days=7)).strftime('%d %b %Y')}

_Keep the compound intelligence compounding._"""

    return report


async def send_weekly_report_telegram():
    """Sends the weekly report via the Telegram bot."""
    try:
        import telegram
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        user_id = os.environ.get("TELEGRAM_ALLOWED_USER_ID")

        if not token or not user_id:
            logger.warning("Telegram credentials not set — skipping weekly report.")
            return

        bot = telegram.Bot(token=token)
        report = generate_weekly_report()
        await bot.send_message(
            chat_id=int(user_id),
            text=report,
            parse_mode="Markdown"
        )
        logger.info("Weekly Telegram report sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send weekly Telegram report: {e}")


if __name__ == "__main__":
    # Test: print report to stdout
    print(generate_weekly_report())
