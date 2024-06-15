import copy
import os
import sys
from pathlib import Path

from loguru import logger
from taskmates.lib.resources_.resources import dump_resource

logger.remove()
file_logger = copy.deepcopy(logger)
logger.add(sys.stderr)

file_logger = file_logger.patch(lambda record: record["extra"].setdefault("base_dir",
                                                                          os.environ.get("TASKMATES_HOME",
                                                                                         "/var/tmp/taskmates")))
file_logger = file_logger.patch(lambda record: record["extra"].setdefault("content", None))
file_logger = file_logger.patch(lambda record: record["extra"].setdefault("request_id", None))

PATH_FORMAT = "{extra[base_dir]}/logs/[{extra[request_id]}][{time:YYYY-MM-DD_HH-mm-ss-SSS}][{module}] {message}"


def file_sink(path_format):
    def sink(message):
        path = path_format.format(**{**message.record})
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        dump_resource(Path(path), message.record["extra"]["content"])

    return sink


file_logger.add(file_sink(path_format=PATH_FORMAT),
                serialize=True,
                level="INFO", )

file_logger.add(sys.stderr,
                # format=f"[file_logger][{{name}}] Writing to \"{PATH_FORMAT}\"",
                level="INFO", )

# TODO
# def test_file_logger(tmp_path):
#     test_message = "Test message"
#     base_dir = tmp_path / "base_dir"
#     base_dir.mkdir(parents=True, exist_ok=True)
#
#     file_logger.debug("foo.txt", content=test_message, base_dir=base_dir)
#
#     logged_files = list(base_dir.glob("logs/*/foo.txt"))
#     print_dir_tree(tmp_path)
#
#     print("Logged files:", logged_files)
#
#     assert list(map(lambda f: Path(f).name, logged_files)) == ["foo.txt"]
#
#     with open(logged_files[0], 'r') as f:
#         log_content = f.read()
#
#     assert log_content.strip() == test_message
