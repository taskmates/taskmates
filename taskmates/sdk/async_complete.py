from typing import Unpack

from typeguard import typechecked

from taskmates.core.completion_engine import CompletionEngine
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.config.updated_config import updated_config
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.contexts import Contexts


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    signals = Signals()
    signals_token = SIGNALS.set(signals)

    completion_chunks = []
    return_value = NOT_SET

    async def process_response_chunk(chunk):
        completion_chunks.append(chunk)

    # TODO
    async def process_error(payload):
        raise payload["error"]

    async def process_return_value(status):
        nonlocal return_value
        return_value = status

    signals.response.response.connect(process_response_chunk)
    signals.output.result.connect(process_return_value)
    signals.response.error.connect(process_error)

    completion_context = Contexts.completion_context.get()

    server_config: ServerConfig = Contexts.server_config.get()
    client_config: ClientConfig = Contexts.client_config.get()

    try:
        with updated_config(Contexts.completion_opts, completion_opts):
            await CompletionEngine().perform_completion(
                completion_context,
                markdown,
                [],
                server_config,
                client_config,
                completion_opts,
                signals)
    finally:
        SIGNALS.reset(signals_token)

    if return_value is not NOT_SET:
        return return_value["result"]

    return "".join(completion_chunks)
