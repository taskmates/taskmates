from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionOpts, COMPLETION_CONTEXT, updated_config, COMPLETION_OPTS
from taskmates.signals import SIGNALS, Signals


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    signals = Signals()
    signals_token = SIGNALS.set(signals)

    completion_chunks = []

    async def process_response_chunk(chunk):
        completion_chunks.append(chunk)

    async def process_error(error):
        raise error

    signals.response.connect(process_response_chunk)
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

    return "".join(completion_chunks)
