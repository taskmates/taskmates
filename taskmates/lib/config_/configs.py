from typing import Callable, Any

from taskmates.lib.config_.flex_dict import FlexDict, not_found
from taskmates.lib.config_.identity import identity


class Configs(FlexDict):
    def __init__(self, *args,
                 missing_fn: Callable[[dict, Any], Any] = None,
                 constructors=None,
                 hash_fn=identity,
                 **kwargs):
        self.constructors = FlexDict(constructors or {}, hash_fn=hash_fn)
        super().__init__(*args, missing_fn=missing_fn, hash_fn=hash_fn, **kwargs)

    def __missing__(self, key: Any) -> Any:
        if key in self.constructors:
            constructed_value = self.constructors[key](self)
            self[key] = constructed_value
            return constructed_value
        else:
            return super().__missing__(key)


def test_constructor():
    d = Configs(constructors={"key1": lambda dct: "constructor_value"})
    assert d["key1"] == "constructor_value"


def test_constructor_and_missing_fn():
    d = Configs(constructors={"key1": lambda dct: "constructor_value"}, missing_fn=not_found)
    assert d["key1"] == "constructor_value"
    assert d["key2"] == "Not Found for key: key2"
