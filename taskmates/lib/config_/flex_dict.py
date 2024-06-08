import uuid
from typing import Callable, Any

from taskmates.lib.config_.identity import identity


class FlexDict(dict):
    def __init__(self, *args,
                 missing_fn: Callable[[dict, Any], Any] = None,
                 hash_fn=identity, **kwargs):
        self.missing_fn = missing_fn
        self.hash_fn = hash_fn
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        return super().__setitem__(self.hash_fn(key), value)

    def setdefault(self: dict, key: Any, default: Any = None) -> Any:
        if key not in self:
            self[key] = default
        return self[key]

    def __delitem__(self, key):
        return super().__delitem__(self.hash_fn(key))

    def __contains__(self, key):
        return super().__contains__(self.hash_fn(key))

    def __getitem__(self, key):
        if key not in self:
            return self.__missing__(key)
        return super().__getitem__(self.hash_fn(key))

    def get(self, key, default=None):
        if key not in self:
            return default
        return super().__getitem__(self.hash_fn(key))

    def __missing__(self, key: Any) -> Any:
        default_value = self.missing_fn(self, key)
        self[key] = default_value
        return default_value


def test_flex_dict():
    def hash_fn(x):
        return x["key"]

    def missing_fn(_dct, key):
        return str(uuid.uuid4())

    cache = FlexDict(hash_fn=hash_fn, missing_fn=missing_fn)
    a = {"key": "A"}
    cache[a] = "A value"
    assert cache[a] == "A value"

    b = {"key": "B"}
    missing = cache[b]
    assert cache[b] is missing


def not_found(_dct, key):
    return f"Not Found for key: {key}"


def test_existing_key():
    d = FlexDict(missing_fn=not_found)
    d["key1"] = "value1"
    assert d["key1"] == "value1"


def test_missing_key():
    d = FlexDict(missing_fn=not_found)
    assert d["key2"] == "Not Found for key: key2"


def test_missing_then_existing_key():
    d = FlexDict(missing_fn=not_found)
    value = d["key2"]
    assert value == "Not Found for key: key2"
    assert d["key2"] == "Not Found for key: key2"


def test_overwrite_missing_key():
    d = FlexDict(missing_fn=not_found)
    assert d["key2"] == "Not Found for key: key2"
    d["key2"] = "new_value"
    assert d["key2"] == "new_value"


def test_multiple_missing_keys():
    d = FlexDict(missing_fn=not_found)
    assert d["key2"] == "Not Found for key: key2"
    assert d["key3"] == "Not Found for key: key3"
    assert d["key4"] == "Not Found for key: key4"
