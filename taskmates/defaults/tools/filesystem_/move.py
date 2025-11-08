import sys
from pathlib import Path

from taskmates.core.workflow_engine.transactions.transaction import TRANSACTION
from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed


def move(source_path, destination_path):
    """
    Moves or renames a file or directory on the user's machine
    :param source_path: the source file or directory path
    :param destination_path: the destination path
    :return: None
    """

    contexts = TRANSACTION.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("move") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("move") or {}).get("deny", None)

    source_obj = Path(source_path)
    dest_obj = Path(destination_path)

    if not source_obj.exists():
        print(f"The source path '{source_path}' does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(source_obj, allow, deny):
        print(f"Access to source path '{source_path}' is not allowed.", file=sys.stderr)
        return None

    if not is_path_allowed(dest_obj, allow, deny):
        print(f"Access to destination path '{destination_path}' is not allowed.", file=sys.stderr)
        return None

    # Create destination parent directory if it doesn't exist
    dest_obj.parent.mkdir(parents=True, exist_ok=True)

    # Move the file or directory
    source_obj.rename(dest_obj)
    return None
