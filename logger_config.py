# logger_config.py

import logging
import logging.handlers
from multiprocessing import Queue
import sys

# Global queue to be used by all processes
log_queue = Queue(-1)

# Module-level variable to track the listener instance
_listener = None

# When True, logs will also be sent to console.
LOG_TO_CONSOLE = False
# following levels from lower to higher: (DEBUG, INFO, WARNING, ERROR, CRITICAL)
default_log_level = logging.DEBUG


def setup_queue_listener(log_queue, logging_file_path='log/doorbell.log', log_level=default_log_level):
    """Configures a QueueListener with desired handlers.

        Args:
        log_queue: The multiprocessing queue to collect log records.
        logging_file_path: Path for the file handler.
        log_level: The logging level for file and console handlers.

    Returns the listener instance, or None if already created.
    """
    global _listener
    if _listener is not None:
        return None  # Listener already created

    """Configures a QueueListener with desired handlers."""
    # Define handlers for the listener
    handlers = []

    # Always add file handler
    file_handler = logging.FileHandler(logging_file_path)   # 'app.log'
    file_handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    )
    file_handler.setLevel(log_level)
    handlers.append(file_handler)

    # Optionally add console handler
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
        )
        # the handler will process messages at DEBUG level and higher (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    _listener = logging.handlers.QueueListener(
        log_queue, *handlers
    )
    _listener.start()
    return _listener


def get_logger(name):
    """Creates a logger that sends log records to the shared queue."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers
    if not any(isinstance(h, logging.handlers.QueueHandler) for h in logger.handlers):
        queue_handler = logging.handlers.QueueHandler(log_queue)
        logger.addHandler(queue_handler)
    return logger
