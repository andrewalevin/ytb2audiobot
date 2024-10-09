import logging
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
console_handler = logging.StreamHandler(sys.stdout)


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


# Add the filter to the handler
console_handler.addFilter(CustomFilter())

# Set up the root logger
logger = logging.getLogger('customLogger')
logger.setLevel(logging.DEBUG)  # Set to the lowest level to catch all messages
logger.addHandler(console_handler)

# Export the logger
__all__ = ['logger']
