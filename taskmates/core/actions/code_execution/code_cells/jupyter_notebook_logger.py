import logging
from pathlib import Path

from taskmates.lib.root_path.root_path import root_path

jupyter_notebook_logger = logging.getLogger(__name__)
jupyter_notebook_logger.handlers.clear()

# Threshold after which the logger will log
jupyter_notebook_logger.level = logging.INFO

# file handler
logs_dir = root_path() / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
log_path = logs_dir / "jupyter_notebook.log"
file_handler = logging.FileHandler(log_path)

# Threshold after which the file handler will log
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n%(message)s\n\n')

file_handler.setFormatter(formatter)

jupyter_notebook_logger.addHandler(file_handler)

# stream handler
handler = logging.StreamHandler()

# Threshold after which the file handler will log
handler.setLevel(logging.WARN)
logging.root.addHandler(handler)


def test_jupyter_notebook_logger(tmp_path):
    # Create a temporary log file
    test_log_path = tmp_path / "test_jupyter_notebook.log"
    test_handler = logging.FileHandler(test_log_path)
    test_handler.setFormatter(formatter)

    # Clear existing handlers and add our test handler
    jupyter_notebook_logger.handlers.clear()
    jupyter_notebook_logger.addHandler(test_handler)

    # Log a test message
    test_message = "Test debug message"
    jupyter_notebook_logger.info(test_message)

    # Verify the message was logged
    assert test_log_path.exists()
    with open(test_log_path, 'r') as f:
        log_content = f.read()
        assert test_message in log_content
