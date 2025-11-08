import pytest
from typing import Union
from typeguard import typechecked

from taskmates.config.find_config_file import find_config_file
from taskmates.config.load_yaml_config import load_yaml_config


@typechecked
def load_model_config(model_alias: Union[str, dict], taskmates_dirs: list) -> dict:
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

    # If model_alias is a dict with kwargs, merge them into client.kwargs
    if isinstance(model_alias, dict) and "kwargs" in model_alias:
        if "client" not in config:
            config["client"] = {}
        if "kwargs" not in config["client"]:
            config["client"]["kwargs"] = {}
        config["client"]["kwargs"].update(model_alias["kwargs"])

    return config


@pytest.fixture
def temp_config_structure(tmp_path):
    temp_dir = tmp_path / "temp_taskmates"
    temp_dir.mkdir(parents=True)

    (temp_dir / ".taskmates").mkdir()
    (temp_dir / "home" / ".taskmates").mkdir(parents=True)
    (temp_dir / "taskmates" / "config").mkdir(parents=True)
    (temp_dir / "taskmates" / "defaults").mkdir(parents=True)

    (temp_dir / ".taskmates" / "models.yaml").write_text("""
model1:
  metadata:
    max_context_window: 100
  client:
    type: gpt
    kwargs:
      model: gpt-1
""")

    (temp_dir / "home" / ".taskmates" / "models.yaml").write_text("""
model2:
  metadata:
    max_context_window: 200
  client:
    type: gpt
    kwargs:
      model: gpt-2
""")

    (temp_dir / "taskmates" / "config" / "models.yaml").write_text("""
model3:
  metadata:
    max_context_window: 300
  client:
    type: gpt
    kwargs:
      model: gpt-3
""")

    (temp_dir / "taskmates" / "defaults" / "models.yaml").write_text("""
model4:
  metadata:
    max_context_window: 400
  client:
    type: gpt
    kwargs:
      model: gpt-4
""")

    return temp_dir


def test_load_model_config(temp_config_structure):
    taskmates_dirs = [
        str(temp_config_structure / ".taskmates"),
        str(temp_config_structure / "home" / ".taskmates"),
        str(temp_config_structure / "taskmates" / "config"),
        str(temp_config_structure / "taskmates" / "defaults")
    ]

    config = load_model_config("model1", taskmates_dirs)
    assert config["metadata"]["max_context_window"] == 100
    assert config["client"]["type"] == "gpt"
    assert config["client"]["kwargs"]["model"] == "gpt-1"

    (temp_config_structure / ".taskmates" / "models.yaml").unlink()
    config = load_model_config("model2", taskmates_dirs)
    assert config["metadata"]["max_context_window"] == 200
    assert config["client"]["type"] == "gpt"
    assert config["client"]["kwargs"]["model"] == "gpt-2"

    (temp_config_structure / "home" / ".taskmates" / "models.yaml").unlink()
    config = load_model_config("model3", taskmates_dirs)
    assert config["metadata"]["max_context_window"] == 300
    assert config["client"]["type"] == "gpt"
    assert config["client"]["kwargs"]["model"] == "gpt-3"

    (temp_config_structure / "taskmates" / "config" / "models.yaml").unlink()
    config = load_model_config("model4", taskmates_dirs)
    assert config["metadata"]["max_context_window"] == 400
    assert config["client"]["type"] == "gpt"
    assert config["client"]["kwargs"]["model"] == "gpt-4"

    with pytest.raises(ValueError, match="Unknown model 'unknown_model'"):
        load_model_config("unknown_model", taskmates_dirs)


def test_load_model_config_with_kwargs_override(temp_config_structure):
    taskmates_dirs = [str(temp_config_structure / ".taskmates")]
    
    model_alias = {
        "name": "model1",
        "kwargs": {"temperature": 0.5}
    }
    
    config = load_model_config(model_alias, taskmates_dirs)
    assert config["client"]["kwargs"]["temperature"] == 0.5
    assert config["client"]["kwargs"]["model"] == "gpt-1"
