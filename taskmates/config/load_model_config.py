import pytest
from typing import Union
from typeguard import typechecked

from taskmates.config.find_config_file import find_config_file
from taskmates.config.load_yaml_config import load_yaml_config


@typechecked
def load_model_config(model_alias: Union[str, dict], taskmates_dirs: list) -> dict:
    # Handle dict case
    if isinstance(model_alias, dict):
        model_name = model_alias.get("name")
        if not model_name:
            raise ValueError(f"Model dict must have a 'name' field: {model_alias}")
    else:
        model_name = model_alias

    config_path = find_config_file("models.yaml", taskmates_dirs)
    if config_path is None:
        raise FileNotFoundError(
            f"Could not find models.yaml in any of the provided directories: {taskmates_dirs}")
    model_config = load_yaml_config(config_path) or {}

    if model_name not in model_config:
        raise ValueError(f"Unknown model {model_name!r}")

    config = model_config[model_name].copy()

    # If model_alias is a dict with kwargs, merge them into the config
    if isinstance(model_alias, dict) and "kwargs" in model_alias:
        config.update(model_alias["kwargs"])

    return config



@pytest.fixture
def temp_config_structure(tmp_path):
    # Create a temporary directory structure
    temp_dir = tmp_path / "temp_taskmates"
    temp_dir.mkdir(parents=True)

    # Create config directories
    (temp_dir / ".taskmates").mkdir()
    (temp_dir / "home" / ".taskmates").mkdir(parents=True)
    (temp_dir / "taskmates" / "config").mkdir(parents=True)
    (temp_dir / "taskmates" / "defaults").mkdir(parents=True)

    # Create config files
    (temp_dir / ".taskmates" / "models.yaml").write_text("""
    model1:
        type: gpt
        max_tokens: 100
    """)

    (temp_dir / "home" / ".taskmates" / "models.yaml").write_text("""
    model2:
        type: gpt
        max_tokens: 200
    """)

    (temp_dir / "taskmates" / "config" / "models.yaml").write_text("""
    model3:
        type: gpt
        max_tokens: 300
    """)

    (temp_dir / "taskmates" / "defaults" / "models.yaml").write_text("""
    model4:
        type: gpt
        max_tokens: 400
    """)

    return temp_dir


def test_load_model_config(temp_config_structure):
    taskmates_dirs = [
        str(temp_config_structure / ".taskmates"),
        str(temp_config_structure / "home" / ".taskmates"),
        str(temp_config_structure / "taskmates" / "config"),
        str(temp_config_structure / "taskmates" / "defaults")
    ]

    # Test loading model from current directory
    config = load_model_config("model1", taskmates_dirs)
    assert config["type"] == "gpt"
    assert config["max_tokens"] == 100

    # Remove current directory config and test loading from home directory
    (temp_config_structure / ".taskmates" / "models.yaml").unlink()
    config = load_model_config("model2", taskmates_dirs)
    assert config["type"] == "gpt"
    assert config["max_tokens"] == 200

    # Remove home directory config and test loading from taskmates directory
    (temp_config_structure / "home" / ".taskmates" / "models.yaml").unlink()
    config = load_model_config("model3", taskmates_dirs)
    assert config["type"] == "gpt"
    assert config["max_tokens"] == 300

    # Remove taskmates directory config and test loading from default config
    (temp_config_structure / "taskmates" / "config" / "models.yaml").unlink()
    config = load_model_config("model4", taskmates_dirs)
    assert config["type"] == "gpt"
    assert config["max_tokens"] == 400

    # Test unknown model
    with pytest.raises(ValueError, match="Unknown model 'unknown_model'"):
        load_model_config("unknown_model", taskmates_dirs)
