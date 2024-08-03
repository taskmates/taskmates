import copy
import json
import textwrap

from typeguard import typechecked

from taskmates.config.load_model_config import load_model_config
from taskmates.lib.openai_.count_tokens import count_tokens
from taskmates.lib.root_path.root_path import root_path


@typechecked
def calculate_max_tokens(messages: list, model_name: str, taskmates_dirs: list):
    images = 0
    if "claude" in model_name:
        return 4096
    if "llama" in model_name:
        return 4096
    else:
        approximate_payload = copy.deepcopy(messages)
        for message in approximate_payload:
            if isinstance(message.get("content", None), list):
                for part in message.get("content", []):
                    if part["type"] != "text":
                        del part["image_url"]
                        images += 1

        available_tokens = load_model_config(model_name, taskmates_dirs)["max_context_window"] - count_tokens(
            json.dumps(approximate_payload, ensure_ascii=False)) - (images * 100)
        return min(available_tokens - 200, 4096)


@typechecked
def get_model_conf(model_alias: str, messages: list, taskmates_dirs: list):
    model_name = load_model_config(model_alias, taskmates_dirs)["model_name"]
    max_tokens = calculate_max_tokens(messages, model_name, taskmates_dirs)

    model_conf = {
        **{"model": model_name,
           "max_tokens": max_tokens,
           "temperature": 0.2,
           "stop": ["\n######"],
           "stream": True}
    }

    return model_conf


def test_handling_wrapped_json_in_payload_role():
    message = '''
    ```json
    {
        "key": "value"
    }
    ```
    '''
    payload = {
        "model": "gpt-4",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": textwrap.dedent(message)
            }
        ]
    }

    default_config_dir = root_path() / "taskmates" / "default_config"
    updated_payload = get_model_conf("gpt-4", payload["messages"], [default_config_dir])
    assert updated_payload == {'max_tokens': 4096,
                               'model': 'gpt-4',
                               'stop': ['\n######'],
                               'stream': True,
                               'temperature': 0.2}


def test_handling_wrapped_json_and_extra_text_in_payload_role():
    payload_message = '''
    ```json
    {
        "key": "value"
    }
    ```
    Some extra text
    '''
    payload = {
        "model": "gpt-4",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "payload",
                "content": textwrap.dedent(payload_message)
            }
        ]
    }
    default_config_dir = root_path() / "taskmates" / "default_config"
    updated_payload = get_model_conf("gpt-4", payload["messages"], [default_config_dir])
    assert updated_payload == {'max_tokens': 4096,
                               'model': 'gpt-4',
                               'stop': ['\n######'],
                               'stream': True,
                               'temperature': 0.2}
