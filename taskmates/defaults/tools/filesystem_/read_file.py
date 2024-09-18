from pathlib import Path

import sys

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.execution_context import EXECUTION_CONTEXT


def read_file(path):
    """
    Reads a FILE from the user's machine and returns its content. DO NOT USE IT ON DIRECTORIES.

    :param path: the path
    :return: the content of the file or None if not allowed
    """
    contexts = EXECUTION_CONTEXT.get().contexts
    completion_opts = contexts["completion_opts"]

    allow = ((completion_opts.get("tools") or {}).get("write_file") or {}).get("allow", "**")
    deny = ((completion_opts.get("tools") or {}).get("write_file") or {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    return path_obj.read_text()
