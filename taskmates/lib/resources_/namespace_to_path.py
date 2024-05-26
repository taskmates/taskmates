from pathlib import Path
from typing import Union, List

from taskmates.lib.root_path.root_path import root_path

Namespace = Union[str, Path, List[str]]


def namespace_to_path(namespace: Namespace) -> Path:
    match namespace:
        case None:
            return root_path()
        case Path():
            return namespace
        case list():
            return root_path() / "app" / "models" / Path(*namespace)
        case str() if namespace.startswith("/") and Path(namespace).is_dir():
            return Path(namespace)
        case str() if namespace.startswith("/") and Path(namespace).is_file():
            return Path(namespace).parent
        case str():
            return namespace_to_path([namespace])
        case _:
            raise NotImplementedError(f"Can't convert {type(namespace)}({namespace}) to path.")
