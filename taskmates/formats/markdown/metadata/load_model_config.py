import yaml

from taskmates.lib.root_path.root_path import root_path


def load_model_config(model_name: str) -> dict:
    config_path = root_path() / 'taskmates/model_config.yaml'

    with open(config_path, 'r') as file:
        model_config = yaml.safe_load(file)

        if model_name not in model_config:
            raise ValueError(f"Unknown model {model_name}")
        return model_config[model_name]
