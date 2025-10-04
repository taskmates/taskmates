from pathlib import Path

import yaml


def load_yaml_config(config_path: Path) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
