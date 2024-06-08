from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import COMPLETION_CONTEXT, CompletionOpts, COMPLETION_OPTS
from taskmates.signals import Signals, SIGNALS


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    signals = Signals()
    signals_token = SIGNALS.set(signals)

    completion_context = COMPLETION_CONTEXT.get()
    completion_opts_token = COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})

    completion_chunks = []

    async def process_response_chunk(chunk):
        completion_chunks.append(chunk)

    async def process_error(error):
        raise error

    signals.response.connect(process_response_chunk)
    signals.error.connect(process_error)

    try:
        await MarkdownCompletionAssistance().perform_completion(
            completion_context,
            markdown,
            signals)
    finally:
        SIGNALS.reset(signals_token)
        COMPLETION_OPTS.reset(completion_opts_token)

    return "".join(completion_chunks)
