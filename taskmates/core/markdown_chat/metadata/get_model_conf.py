import copy
import json
from typing import Union

from typeguard import typechecked

from taskmates.config.load_model_config import load_model_config
from taskmates.lib.openai_.count_tokens import count_tokens


@typechecked
def calculate_max_tokens(messages: list, model_config: dict):
    model_name = model_config.get("model_name") or model_config.get("model") or ""
    max_context_window = model_config["max_context_window"]

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

        available_tokens = max_context_window - count_tokens(
            json.dumps(approximate_payload, ensure_ascii=False)) - (images * 100)
        return min(available_tokens - 200, 4096)


@typechecked
def get_model_conf(model_alias: Union[str, dict],
                   messages: list,
                   taskmates_dirs: list):
    # if isinstance(model_alias, dict) and model_alias.get("name") == "fixture":
    #     # Return a config for the fixture model
    #     return {
    #         "model_name": "fixture",
    #         "fixture_path": model_alias["args"]["path"],
    #     }
    model_config = load_model_config(model_alias, taskmates_dirs)
    max_tokens = calculate_max_tokens(messages, model_config)

    model_conf = {
        **model_config,
        "max_tokens": max_tokens
    }

    if "gpt-oss" in model_conf["model"]:
        model_conf.update({
            "reasoning_effort": "high",
        })

    if "gpt-5" not in model_conf["model"]:
        model_conf.update({
            "temperature": 0.2,
        })

    # if "claude" in model_conf["model"]:
    #     model_conf.update({
    #         "thinking": {"type": "enabled", "budget_tokens": 2000},
    #         "temperature": 1
    #     })

    model_conf.update({
        "stop": ["^######"],
    })

    # TODO: this only works with OpenAI models
    # "seed": int(random() * 1000000)

    return model_conf
