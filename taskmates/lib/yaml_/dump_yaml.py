import textwrap
from io import StringIO

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
from taskmates.lib.yaml_.load_yaml import load_yaml


class MyYAML(YAML):
    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        super().dump(data, stream, **kw)
        if inefficient:
            return stream.getvalue()

    @staticmethod
    def represent_str(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', LiteralScalarString(data), style='|')


def dump_yaml(data):
    my_yaml = MyYAML()
    my_yaml.representer.add_representer(str, my_yaml.represent_str)
    if isinstance(data, str):
        dump = "|2-\n" + textwrap.indent(data, "  ")
    else:
        dump = my_yaml.dump(data)

        try:
            yaml.safe_load(dump)
        except yaml.YAMLError:
            raise ValueError(f"YAML dump is invalid:\n{dump}")

    return dump


def test_dump_str():
    yaml_str = "a\n{{ b }}\nc"

    assert yaml.safe_load(dump_yaml(yaml_str)) == yaml_str
    assert load_yaml(dump_yaml(yaml_str)) == yaml_str


def test_dump_dct():
    dct = {"a": "a\n{{ b }}\nc"}

    assert yaml.safe_load(dump_yaml(dct)) == dct
    assert load_yaml(dump_yaml(dct)) == dct
