from typing import Unpack

from typeguard import typechecked

from taskmates.config.completion_opts import CompletionOpts
from taskmates.contexts import CONTEXTS
from taskmates.core.completion_engine import CompletionEngine
from taskmates.lib.context_.context_fork import context_fork
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.signals.signals import SIGNALS, Signals


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    # TODO use completion_opts
    with temp_context(SIGNALS, Signals()) as signals:
        # TODO create handlers for these

        completion_chunks = []
        async def process_response_chunk(chunk):
            completion_chunks.append(chunk)

        # TODO
        async def process_error(payload):
            raise payload["error"]

        return_value = NOT_SET
        async def process_return_value(status):
            nonlocal return_value
            return_value = status

        signals.response.response.connect(process_response_chunk)
        signals.output.result.connect(process_return_value)
        signals.response.error.connect(process_error)

        with context_fork(CONTEXTS) as contexts:
            await CompletionEngine().perform_completion(
                history=markdown,
                incoming_messages=[],
                step_contexts=contexts,
                signals=signals)

        if return_value is not NOT_SET:
            return return_value["result"]

        return "".join(completion_chunks)
