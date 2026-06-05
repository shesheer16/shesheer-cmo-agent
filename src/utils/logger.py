import sys
from pathlib import Path
from loguru import logger

# Ensure log directory exists
log_dir = Path("data/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Remove default handler
logger.remove()

LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {module} | {level: <8} | {message}"

# 1. Stdout (coloured, all levels)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan>{module}</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
    enqueue=True,
    colorize=True
)

# 2. app.log — all logs, rotate daily, keep 7 days
logger.add(
    log_dir / "app.log",
    format=LOG_FORMAT,
    rotation="00:00",
    retention="7 days",
    enqueue=True,
)

# 3. errors.log — ERROR and above only
logger.add(
    log_dir / "errors.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="14 days",
    enqueue=True,
)

# 4. cost.log — filter by 'cost' in message
logger.add(
    log_dir / "cost.log",
    format=LOG_FORMAT,
    filter=lambda record: "cost" in record["message"].lower() or "token" in record["message"].lower(),
    rotation="1 week",
    retention="4 weeks",
    enqueue=True,
)

# 5. ingestion.log — filter by ingestion/pipeline modules
logger.add(
    log_dir / "ingestion.log",
    format=LOG_FORMAT,
    filter=lambda record: record["module"] in (
        "pdf_processor", "web_scraper", "youtube_ingester",
        "social_scheduler", "embedder", "chunker", "source_registry"
    ),
    rotation="1 week",
    retention="4 weeks",
    enqueue=True,
)
