import logging
import os
import sys


# Custom date format without milliseconds
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Create custom formatters for all levels without milliseconds
DEBUG_FORMATTER = logging.Formatter('%(asctime)s - 🔵 %(message)s - DEBUG', datefmt=DATE_FORMAT)
INFO_FORMATTER = logging.Formatter('%(asctime)s - 🟢 %(message)s - INFO', datefmt=DATE_FORMAT)
WARNING_FORMATTER = logging.Formatter('%(asctime)s - 🟠 %(message)s - WARNING', datefmt=DATE_FORMAT)
ERROR_FORMATTER = logging.Formatter('%(asctime)s - 🔴 %(message)s - ERROR', datefmt=DATE_FORMAT)
CRITICAL_FORMATTER = logging.Formatter('%(asctime)s - 🟣 %(message)s - CRITICAL', datefmt=DATE_FORMAT)

# Create a stream handler
console_handler = logging.StreamHandler()

BOLD_GREEN = "\033[1;32m"  # Bold green
RESET = "\033[0m"          # Reset

# Custom filter to apply different formatters based on log level
class CustomFilter(logging.Filter):
    def filter(self, record):
        if record.levelno == logging.DEBUG:
            console_handler.setFormatter(DEBUG_FORMATTER)
        elif record.levelno == logging.INFO:
            console_handler.setFormatter(INFO_FORMATTER)
        elif record.levelno == logging.WARNING:
            console_handler.setFormatter(WARNING_FORMATTER)
        elif record.levelno == logging.ERROR:
            console_handler.setFormatter(ERROR_FORMATTER)
        elif record.levelno == logging.CRITICAL:
            console_handler.setFormatter(CRITICAL_FORMATTER)
        return True


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[1;34m"
    reset = "\x1b[0m"

    format = "%(asctime)s - %(message)s - (%(filename)s:%(lineno)d) - %(levelname)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Add the filter to the handler
console_handler.addFilter(CustomFilter())

# Set up the root logger
logger = logging.getLogger('customLogger')

#logger.addHandler(console_handler)
ch = logging.StreamHandler()
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)
logger.setLevel(logging.INFO)
logger.propagate = False

if os.getenv('DEBUG', 'false') == 'true':
    logger.setLevel(logging.DEBUG)

# Export the logger
__all__ = ['logger']


