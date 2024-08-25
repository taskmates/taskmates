import fnmatch
from pathlib import Path

import sys

from taskmates.contexts import CONTEXTS


def is_path_allowed(path, allow_pattern, deny_pattern):
    """
    Check if a path is allowed based on allow and deny patterns.

    :param path: Path to check
    :param allow_pattern: Pattern for allowed paths
    :param deny_pattern: Pattern for denied paths
    :return: True if path is allowed, False otherwise
    """
    path_str = str(path)
    if deny_pattern and fnmatch.fnmatch(path_str, deny_pattern):
        return False
    return fnmatch.fnmatch(path_str, allow_pattern)


def read_file(path):
    """
    Reads a FILE from the user's machine and returns its content. DO NOT USE IT ON DIRECTORIES.

    :param path: the path
    :return: the content of the file or None if not allowed
    """
    contexts = CONTEXTS.get()
    completion_opts = contexts["completion_opts"]
    allow = completion_opts.get("tools", {}).get("read_file", {}).get("allow", "**")
    deny = completion_opts.get("tools", {}).get("read_file", {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    return path_obj.read_text()
