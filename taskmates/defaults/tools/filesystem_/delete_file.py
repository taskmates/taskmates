import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.transaction import TRANSACTION


def delete_file(path):
    """
    Deletes a file from the user's machine
    :param path: the path to the file to delete
    :return: None
    """

    contexts = TRANSACTION.get().execution_context.context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("delete_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("delete_file") or {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    path_obj.unlink()
    return None
