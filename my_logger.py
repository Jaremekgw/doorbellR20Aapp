import logging
import threading
import sys

# Configure logging
     # logging.DEBUG  if INFO you won't see DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(filename)s+%(lineno)d] %(message)s',
    #handlers=[
    #    logging.FileHandler("log/doorbell_app.log"),
    #    logging.StreamHandler(sys.stdout)
    #]
)
"""
inne formaty:
    '%(filename)s:%(lineno)d [Thread-%(thread)d] - %(levelname)s - %(message)s'
    '%(filename)s:%(lineno)d - %(levelname)s - %(message)s'
"""

# Create Logger A (with thread info)
logger_thd = logging.getLogger('with_thread')
logger_thd.setLevel(logging.DEBUG)
handler_with_thread = logging.StreamHandler()
formatter_with_thread = logging.Formatter(
    '[Thread-%(thread)d]'
)
handler_with_thread.setFormatter(formatter_with_thread)
logger_thd.addHandler(handler_with_thread)

# Create Logger B (with process info)
logger_pid = logging.getLogger('with_pid')
logger_pid.setLevel(logging.DEBUG)
handler_with_pid = logging.StreamHandler()
formatter_with_pid = logging.Formatter(
    '%(asctime)s [name=%(name)s][pid=%(process)d] [%(filename)s+%(lineno)d] %(message)s'
)
handler_with_pid.setFormatter(formatter_with_pid)
logger_pid.addHandler(handler_with_pid)

"""
Example usage:
logging.info()
logging.debug()
logging.warning()
logging.error()
logging.critical()

prallel logs to file and console:

import logging

# Step 2: Create a logger
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages

# Step 3: Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('app.log')  # Logs will be written to 'app.log'

# Step 4: Set log levels for handlers
console_handler.setLevel(logging.INFO)  # Console will show INFO and above
file_handler.setLevel(logging.DEBUG)    # File will capture DEBUG and above

# Step 5: Create formatters
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Step 6: Add formatters to handlers
console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

# Step 7: Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Step 8: Log messages
logger.debug("This is a DEBUG message.")    # Will appear only in 'app.log'
logger.info("This is an INFO message.")     # Will appear in both console and 'app.log'
logger.warning("This is a WARNING message.")# Will appear in both
logger.error("This is an ERROR message.")   # Will appear in both
logger.critical("This is a CRITICAL message.") # Will appear in both

"""
