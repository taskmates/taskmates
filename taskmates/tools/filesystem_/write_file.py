from pathlib import Path


def write_file(path, content):
    """
    Writes content to a file on the user's machine
    :param path: the path
    :param content: the content
    :return: None
    """
    return Path(path).write_text(content)
