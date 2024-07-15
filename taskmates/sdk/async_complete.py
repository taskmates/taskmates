from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionOpts, COMPLETION_CONTEXT, updated_config, COMPLETION_OPTS
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.signals import SIGNALS, Signals


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    signals = Signals()
    signals_token = SIGNALS.set(signals)

    completion_chunks = []
    return_value = NOT_SET

    async def process_response_chunk(chunk):
        completion_chunks.append(chunk)

    async def process_error(payload):
        raise payload["error"]

    async def process_return_value(status):
        nonlocal return_value
        return_value = status

    signals.response.connect(process_response_chunk)
    signals.return_value.connect(process_return_value)
    signals.error.connect(process_error)

    completion_context = COMPLETION_CONTEXT.get()
    try:
        with updated_config(COMPLETION_OPTS, completion_opts):
            await MarkdownCompletionAssistance().perform_completion(
                completion_context,
                markdown,
                signals)
    finally:
        SIGNALS.reset(signals_token)

    if return_value is not NOT_SET:
        return return_value["result"]

    return "".join(completion_chunks)
