import sys
from loguru import logger
from src.core.config import settings

logger.remove()

log_level = "DEBUG" if settings.debug else "INFO"

logger.add(
    sys.stdout,
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    colorize=True,
)
