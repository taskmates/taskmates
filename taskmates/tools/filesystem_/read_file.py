from pathlib import Path


async def read_file(path):
    """
    Reads a FILE from the user's machine and returns its content. DO NOT USE IT ON DIRECTORIES.

    :param path: the path
    :return: the content of the file
    """
    return Path(path).read_text()
