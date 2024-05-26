import logging
import os
import re
from datetime import datetime


def _sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


class FilePerEntryHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET, log_dir='logs'):
        super().__init__(level=level)
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir

    def emit(self, record):
        filename = self.format(record)
        # filename = f"{_sanitize_filename(record.getMessage())}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_path = os.path.join(self.log_dir, filename)
        with open(file_path, 'a') as log_file:
            log_file.write(record.getMessage())


# Test cases

def test_log_filename_format(tmp_path):
    logger = logging.getLogger('test_logger_filename_format')
    logger.setLevel(logging.INFO)
    handler = FilePerEntryHandler(log_dir=tmp_path)
    logger.addHandler(handler)

    test_message = "Info log entry"
    logger.info(test_message)

    log_files = os.listdir(tmp_path)
    assert len(log_files) == 1
    assert test_message in log_files[0]


def test_log_file_content(tmp_path):
    logger = logging.getLogger('test_logger_file_content')
    logger.setLevel(logging.INFO)
    handler = FilePerEntryHandler(log_dir=tmp_path)
    logger.addHandler(handler)

    test_message = "Info log entry"
    logger.info(test_message)

    log_files = os.listdir(tmp_path)
    assert len(log_files) == 1

    with open(os.path.join(tmp_path, log_files[0]), 'r') as file:
        assert test_message in file.read()
