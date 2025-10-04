import sys
from pathlib import Path

from taskmates.core.workflow_engine.transaction import TRANSACTION
from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed


def create_directory(path, parents=True, exist_ok=True):
    """
    Creates a directory on the user's machine
    :param path: the directory path to create
    :param parents: if True, create parent directories as needed (default: True)
    :param exist_ok: if True, don't raise error if directory already exists (default: True)
    :return: True if successful, None if not allowed or error occurred
    """

    contexts = TRANSACTION.get().execution_context.context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("create_directory") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("create_directory") or {}).get("deny", None)

    path_obj = Path(path)

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to create directory '{path}' is not allowed.", file=sys.stderr)
        return None

    try:
        path_obj.mkdir(parents=parents, exist_ok=exist_ok)
        return True
    except Exception as e:
        print(f"Error creating directory '{path}': {e}", file=sys.stderr)
        return None
