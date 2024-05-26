import os
from pathlib import Path


def with_extension(path, *suffix):
    if not isinstance(path, Path):
        return str(with_extension(Path(path), *suffix))

    path = str(path)
    path, ext = os.path.splitext(path)

    if len(suffix) == 1:
        return Path(f"{path}.{suffix[0]}")
    else:
        return Path(f"{path}_{'.'.join(suffix)}")


def test_filename_with_extension():
    assert with_extension("hello.py", "txt") == "hello.txt"
    assert with_extension("hello.py", "txt", "md") == "hello_txt.md"


def test_path_with_extension():
    assert with_extension(Path("/mypath/hello.py"), "txt") == Path("/mypath/hello.txt")
    assert with_extension(Path("/mypath/hello.py"), "txt", "md") == Path("/mypath/hello_txt.md")
