import importlib
import os
from langchain_core.language_models import BaseChatModel
from typeguard import typechecked


@typechecked
def get_model_client(model_conf: dict) -> BaseChatModel:
    client_type = model_conf['client']['type']
    client_kwargs = model_conf['client'].get('kwargs', {}).copy()

    # Dynamically import the class from the client_type string
    module_path, class_name = client_type.rsplit(".", 1)
    module = importlib.import_module(module_path)
    llm_class = getattr(module, class_name)

    # Handle env: prefix for api_key
    if "api_key" in client_kwargs:
        api_key = client_kwargs["api_key"]
        if isinstance(api_key, str) and api_key.startswith('env:'):
            client_kwargs["api_key"] = os.getenv(api_key[4:])

    # Instantiate and return the LLM
    return llm_class(**client_kwargs)
