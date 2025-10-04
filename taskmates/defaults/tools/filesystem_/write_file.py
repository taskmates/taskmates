import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.transaction import TRANSACTION


def write_file(path, content):
    """
    Writes content to a file on the user's machine
    :param path: the path
    :param content: the content
    :return: None
    """

    contexts = TRANSACTION.get().execution_context.context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("write_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("write_file") or {}).get("deny", None)

    path_obj = Path(path)

    # Check if the path is allowed before creating anything
    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    # Create parent directories if they don't exist
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Write the content to the file
    return path_obj.write_text(content)
