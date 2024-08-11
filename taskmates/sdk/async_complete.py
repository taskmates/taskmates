from typing import Unpack

from typeguard import typechecked

from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.context_fork import context_fork
from taskmates.contexts import CONTEXTS
from taskmates.core.completion_engine import CompletionEngine
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.signals.signals import SIGNALS, Signals


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

    try:
        with context_fork(CONTEXTS) as contexts:
            await CompletionEngine().perform_completion(
                history=markdown,
                incoming_messages=[],
                contexts=contexts,
                signals=signals)
    finally:
        SIGNALS.reset(signals_token)

    if return_value is not NOT_SET:
        return return_value["result"]

    return "".join(completion_chunks)
