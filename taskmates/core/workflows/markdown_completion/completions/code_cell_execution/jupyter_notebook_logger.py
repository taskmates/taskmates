import logging
import os

level = os.environ.get("TASKMATES_LOG_LEVEL", "WARNING").upper()

jupyter_notebook_logger = logging.getLogger("jupyter_notebook")
jupyter_notebook_logger.setLevel(level)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(level)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
jupyter_notebook_logger.addHandler(ch)
