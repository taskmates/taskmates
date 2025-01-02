import logging
import sys
from pathlib import Path

from taskmates.lib.root_path.root_path import root_path

# Create logger with a specific name
jupyter_notebook_logger = logging.getLogger(__name__)
jupyter_notebook_logger.handlers.clear()

# Important: Set propagate to False to prevent messages from being passed to ancestor loggers
jupyter_notebook_logger.propagate = False

# Set base level to DEBUG to allow processing of all messages
jupyter_notebook_logger.setLevel(logging.DEBUG)

# file handler
logs_dir = root_path() / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
log_path = logs_dir / "jupyter_notebook.log"
file_handler = logging.FileHandler(log_path)

# Log everything to file
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
file_handler.setFormatter(formatter)
jupyter_notebook_logger.addHandler(file_handler)

# stream handler
stream_handler = logging.StreamHandler(sys.stdout)

# Log INFO and above to console
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
jupyter_notebook_logger.addHandler(stream_handler)


def test_jupyter_notebook_logger(tmp_path, capsys):
    # Create a temporary log file
    test_log_path = tmp_path / "test_jupyter_notebook.log"
    test_file_handler = logging.FileHandler(test_log_path)
    test_file_handler.setFormatter(formatter)
    test_file_handler.setLevel(logging.DEBUG)

    test_stream_handler = logging.StreamHandler(sys.stdout)
    test_stream_handler.setFormatter(formatter)
    test_stream_handler.setLevel(logging.INFO)

    # Clear existing handlers and add our test handlers
    jupyter_notebook_logger.handlers.clear()
    jupyter_notebook_logger.addHandler(test_file_handler)
    jupyter_notebook_logger.addHandler(test_stream_handler)

    # Log messages at different levels
    debug_message = "Test debug message"
    info_message = "Test info message"
    warn_message = "Test warning message"

    jupyter_notebook_logger.debug(debug_message)
    jupyter_notebook_logger.info(info_message)
    jupyter_notebook_logger.warning(warn_message)

    # Verify file logging (should contain all messages)
    with open(test_log_path, 'r') as f:
        log_content = f.read()
        assert debug_message in log_content
        assert info_message in log_content
        assert warn_message in log_content

    # Verify console output (should only contain INFO and above)
    captured = capsys.readouterr()
    assert debug_message not in captured.out
    assert info_message in captured.out
    assert warn_message in captured.out
