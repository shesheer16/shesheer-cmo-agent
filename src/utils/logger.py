import sys
from loguru import logger

# Remove default handler
logger.remove()

# Add structured handler
# Format: timestamp, module, level, message
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan>{module}</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
    enqueue=True,
    colorize=True
)
