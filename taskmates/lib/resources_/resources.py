import glob
import json
import os
from pathlib import Path

from taskmates import patches
from taskmates.lib.resources_.namespace_to_path import namespace_to_path, Namespace
from taskmates.lib.yaml_.dump_yaml import dump_yaml
from taskmates.lib.yaml_.load_yaml import load_yaml

patches.patch_json()
patches.patch_yaml()

cache = {}


def read_str(path, namespace=None):
    namespace_path = namespace_to_path(namespace)
    with open(namespace_path / path, "r") as f:
        return f.read()


def resource_exists(path, namespace=None):
    resolved_path: Path = namespace_to_path(namespace) / path
    return resolved_path.exists()


def config_exists(namespace):
    return bool(len(glob.glob("value*.yaml", recursive=False, root_dir=str(namespace_to_path(namespace)))))


def load_resource(path, namespace=None, load_unsupported=False):
    resolved_path: Path = namespace_to_path(namespace) / path
    cache_key = (str(resolved_path), os.path.getmtime(resolved_path))
    if cache_key in cache:
        return cache[cache_key]
    if str(resolved_path).endswith(".json"):
        value = json.loads(read_str(path, namespace))
    elif str(resolved_path).endswith(".yaml"):
        value = load_yaml(read_str(path, namespace))
    elif not load_unsupported:
        raise NotImplementedError(f"Reading {path} is not supported.")
    else:
        value = read_str(path, namespace)
    cache[cache_key] = value
    return value


def dump_resource(path: Path, content, dump_unsupported=False) -> Path:
    if path.name.endswith(".json"):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    elif path.name.endswith(".yaml"):
        content = dump_yaml(content)
    elif path.name.endswith(".txt") or path.name.endswith(".md"):
        pass
    elif not dump_unsupported:
        raise NotImplementedError(f"Writing {path} is not supported.")

    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

    return path


def key(namespace: Namespace) -> str:
    return ".".join(namespace)


def resource_extend(path, value):
    if path.exists():
        existing = load_resource(path)
        value = [*existing, *value]
    dump_resource(path, value)
