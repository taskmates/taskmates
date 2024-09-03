import toml

from taskmates.lib.root_path.root_path import root_path


def get_version():
    pyproject_path = root_path() / "pyproject.toml"
    try:
        pyproject_data = toml.load(pyproject_path)
        return pyproject_data["tool"]["poetry"]["version"]
    except (FileNotFoundError, KeyError):
        return "unknown"


__version__ = get_version()

if __name__ == "__main__":
    print(__version__)
