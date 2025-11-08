from typing import Union

from typeguard import typechecked

from taskmates.config.load_model_config import load_model_config
from taskmates.defaults.settings import Settings


@typechecked
def config_model_conf(model_alias: Union[str, dict],
                      stop_sequences: list | None = None,
                      input_tokens: int = 0,
                      ):
    taskmates_dirs = Settings.get()["runner_environment"]["taskmates_dirs"]

    model_config = load_model_config(model_alias, taskmates_dirs)
    max_context_window = model_config["metadata"]["max_context_window"]
    max_tokens = max_context_window - input_tokens

    if "max_output_tokens" in model_config["metadata"]:
        max_output_tokens = model_config["metadata"]["max_output_tokens"]
        max_tokens = min(max_tokens, max_output_tokens)

    # Get model name from client kwargs
    model_kwargs = model_config.get("client", {}).get("kwargs", {})

    model_kwargs = {
        **model_kwargs,
        "max_tokens": max_tokens
    }

    # if "claude" in model_conf["model"]:
    #     model_conf.update({
    #         "thinking": {"type": "enabled", "budget_tokens": 2000},
    #         "temperature": 1
    #     })

    model_kwargs.update({"stop": stop_sequences})

    # TODO: this only works with OpenAI models
    # "seed": int(random() * 1000000)

    model_config["client"].update({
        "kwargs": model_kwargs,
    })
    return model_config
