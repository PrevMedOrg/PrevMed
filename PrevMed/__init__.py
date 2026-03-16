from loguru import logger
from pathlib import Path
import sys

# Remove default handler to configure our own
logger.remove()

# Add console handler at INFO level (can be reconfigured to DEBUG with --debug flag)
_console_handler_id = logger.add(
    sys.stderr,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
)

# Configure loguru logger to save to ./logs directory
# Create logs directory if it doesn't exist
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

# Add file handler at INFO level
_file_handler_id = logger.add(
    f"{LOG_DIR}/survey_{{time:YYYY-MM-DD}}.log",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep 30 days of logs
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
)


def enable_debug_console():
    """Reconfigure console logger to DEBUG level."""
    global _console_handler_id
    logger.remove(_console_handler_id)
    _console_handler_id = logger.add(
        sys.stderr,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )


from PrevMed.utils.version import __VERSION__

__all__ = ["__VERSION__", "enable_debug_console"]
