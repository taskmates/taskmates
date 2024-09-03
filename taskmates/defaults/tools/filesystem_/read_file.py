from pathlib import Path

import sys

from taskmates.runner.contexts.contexts import CONTEXTS
from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed


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
