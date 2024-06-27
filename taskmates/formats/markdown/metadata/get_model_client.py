import os

import openai as oai
from typeguard import typechecked

from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.anthropic_openai_adapter import \
    AsyncAnthropicOpenAIAdapter
from taskmates.assistances.chat_completion.openai_adapters.echo.echo import Echo
from taskmates.assistances.chat_completion.openai_adapters.echo.quote import Quote
from taskmates.formats.markdown.metadata.load_model_config import load_model_config


@typechecked
def get_model_client(model_name: str):
    model_config = load_model_config(model_name)

    model_spec = model_config
    client_type = model_spec['client_type']
    endpoint = model_spec.get('endpoint')
    api_key = model_spec.get('api_key')

    if client_type == 'openai':
        client = oai.AsyncOpenAI(base_url=endpoint)
        if api_key and api_key.startswith('env:'):
            client.api_key = os.getenv(api_key[4:])
    elif client_type == 'anthropic':
        client = AsyncAnthropicOpenAIAdapter()
    elif client_type == 'echo':
        client = Echo()
    elif client_type == 'quote':
        client = Quote()
    else:
        raise ValueError(f"Unknown client type {client_type}")

    return client
