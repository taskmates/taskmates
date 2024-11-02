import importlib.metadata

from taskmates.lib.root_path.root_path import root_path

__version__ = importlib.metadata.version("taskmates")

if __name__ == "__main__":
    print(__version__)
