
import logging
import sys
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for production log aggregation."""

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "guild_id", "payment_id", "discord_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)

def setup_logging(name="bot_fazendeiro", log_file="bot.log", level=logging.INFO):
    """
    Sets up a centralized logger with console and file handlers.
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times (if called repeatedly)
    if logger.hasHandlers():
        return logger

    use_json = os.getenv("LOG_JSON", "0") == "1"
    formatter = JsonFormatter() if use_json else logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler (Rotating)
    file_handler = RotatingFileHandler(
        f"logs/{log_file}", maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create a default logger instance for easy import
logger = setup_logging()
