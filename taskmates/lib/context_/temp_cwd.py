import os
from contextlib import contextmanager


@contextmanager
def temp_cwd(path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)
