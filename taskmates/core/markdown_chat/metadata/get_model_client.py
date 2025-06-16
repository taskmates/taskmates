import inspect

from langchain_core.language_models import BaseChatModel
from typeguard import typechecked


@typechecked
def get_model_client(model_spec: dict) -> BaseChatModel:
    client_type = model_spec['client_type']

    # Dynamically import the class from the client_type string
    if "." in client_type:
        module_path, class_name = client_type.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        llm_class = getattr(module, class_name)
    else:
        raise ValueError(f"Invalid client_type: {client_type}. Must be a full import path.")

    # Prepare kwargs for the LLM constructor
    # Only pass keys that are accepted by the LLM class

    llm_init_params = inspect.signature(llm_class.__init__).parameters
    allowed_keys = set(llm_init_params.keys()) - {"self", "args", "kwargs"}

    # Remove non-LLM keys
    model_name = model_spec.get("model", model_spec.get("model_name"))
    if "gpt" in model_name or "gemini" in model_name:
        exclude_keys = {"client_type", "max_context_window", "stop"}
    else:
        exclude_keys = {"client_type", "max_context_window"}
    model_spec_clean = {k: v for k, v in model_spec.items() if k not in exclude_keys}

    # Special handling for OpenAI models: map endpoint -> openai_api_base
    if "langchain_openai" in client_type and "endpoint" in model_spec_clean:
        model_spec_clean["openai_api_base"] = model_spec_clean.pop("endpoint")

    # If only **kwargs, pass all config keys except excluded
    if not allowed_keys:
        kwargs = dict(model_spec_clean)
    else:
        kwargs = {k: v for k, v in model_spec_clean.items() if k in allowed_keys}

    # Always ensure 'model' is present if 'model_name' is present
    if "model" not in kwargs and "model_name" in model_spec_clean:
        kwargs["model"] = model_spec_clean["model_name"]

    # Pass endpoint/api_key if accepted
    if "endpoint" in model_spec and "endpoint" in allowed_keys:
        kwargs["endpoint"] = model_spec["endpoint"]

    if "api_key" in model_spec:
        api_key = model_spec["api_key"]
        if isinstance(api_key, str) and api_key.startswith('env:'):
            import os
            kwargs["api_key"] = os.getenv(api_key[4:])
        else:
            kwargs["api_key"] = api_key

    # Instantiate and return the LLM
    return llm_class(**kwargs)
