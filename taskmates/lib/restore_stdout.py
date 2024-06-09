import sys
from contextlib import contextmanager


@contextmanager
def restore_stdout():
    original_stdout = sys.stdout
    try:
        sys.stdout = sys.__stdout__
        yield
    finally:
        sys.stdout = original_stdout
