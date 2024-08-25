from pathlib import Path

from taskmates.contexts import CONTEXTS
from taskmates.tools.filesystem_.is_path_allowed import is_path_allowed


def write_file(path, content):
    """
    Writes content to a file on the user's machine
    :param path: the path
    :param content: the content
    :return: None
    """

    contexts = CONTEXTS.get()
    completion_opts = contexts["completion_opts"]

    allow = completion_opts.get("tools", {}).get("write_file", {}).get("allow", "**")
    deny = completion_opts.get("tools", {}).get("write_file", {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    return Path(path).write_text(content)
