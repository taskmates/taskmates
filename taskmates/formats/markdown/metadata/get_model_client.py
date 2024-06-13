import os

import openai as oai

from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.anthropic_openai_adapter import \
    AsyncAnthropicOpenAIAdapter
from taskmates.assistances.chat_completion.openai_adapters.echo.echo import Echo


def get_model_client(model_conf: dict):
    if model_conf["model"] in ("codeqwen",):
        client = oai.AsyncOpenAI(base_url="http://localhost:11434/v1")
        client.api_key = os.getenv('GROQ_API_KEY')
    elif model_conf["model"] in ("mixtral-8x7b-32768", "llama3-70b-8192"):
        client = oai.AsyncOpenAI(base_url="https://api.groq.com/openai/v1")
        client.api_key = os.getenv('GROQ_API_KEY')
    elif "llama" in model_conf["model"]:
        client = oai.AsyncOpenAI(base_url="http://localhost:8001/v1")
    elif "claude" in model_conf["model"]:
        client = AsyncAnthropicOpenAIAdapter()
    elif "gpt" in model_conf["model"]:
        client = oai.AsyncOpenAI()
    elif "echo" in model_conf["model"]:
        client = Echo()
    else:
        raise ValueError(f"Unknown model {model_conf['model']}")
    return client
