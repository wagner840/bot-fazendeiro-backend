
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

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

    # Formatter
    formatter = logging.Formatter(
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
