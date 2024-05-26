import json
import yaml

from ruamel.yaml.scalarstring import LiteralScalarString


def load_yaml(yaml_str):
    result = yaml.safe_load(yaml_str)
    return result
