import logging
import os
import re
from datetime import datetime


def _sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


class FilePerEntryLogger(logging.Logger):
    def __init__(self, name, log_dir='logs', log_format='%(asctime)s_%(levelname)s'):
        super().__init__(name)
        self.log_dir = log_dir
        self.log_format = log_format
        os.makedirs(self.log_dir, exist_ok=True)
        self.formatter = logging.Formatter(log_format, datefmt='%Y%m%d_%H%M%S')

    def _log_file_path(self, record):
        base_filename = self.formatter.format(record)
        sanitized_filename = _sanitize_filename(base_filename)
        return os.path.join(self.log_dir, f"{sanitized_filename}.log")

    def handle(self, record):
        file_path = self._log_file_path(record)
        with open(file_path, 'w') as log_file:
            log_file.write(record.getMessage())


# Test cases

def test_log_filename_format(tmp_path):
    logger = FilePerEntryLogger('test_logger', log_dir=tmp_path)
    logger.setLevel(logging.INFO)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_message = "Info log entry"
    logger.info(test_message)

    expected_filename = f"{timestamp}_INFO.log"
    log_files = os.listdir(tmp_path)
    assert len(log_files) == 1
    assert expected_filename == log_files[0]


def test_log_file_content(tmp_path):
    logger = FilePerEntryLogger('test_logger', log_dir=tmp_path)
    logger.setLevel(logging.INFO)

    test_message = "Info log entry"
    logger.info(test_message)

    log_files = os.listdir(tmp_path)
    assert len(log_files) == 1

    with open(os.path.join(tmp_path, log_files[0]), 'r') as file:
        assert file.read() == test_message
