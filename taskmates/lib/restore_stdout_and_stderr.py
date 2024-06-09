import sys
from contextlib import contextmanager


@contextmanager
def restore_stdout_and_stderr():
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    try:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        yield
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
