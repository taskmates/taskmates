import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.transactions.transaction import TRANSACTION


def append_to_file(path, content):
    """
    Appends content to a file on the user's machine
    :param path: the path
    :param content: the content to append
    :return: None
    """

    contexts = TRANSACTION.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("append_to_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("append_to_file") or {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    with open(path_obj, 'a') as f:
        f.write(content)
    return None
