import os
from contextlib import contextmanager


@contextmanager
def temp_environ(env):
    old_environ = dict(os.environ)
    os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
