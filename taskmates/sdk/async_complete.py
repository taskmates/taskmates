from typing import Unpack

from typeguard import typechecked

from taskmates.config.completion_opts import CompletionOpts
from taskmates.contexts import CONTEXTS
from taskmates.core.completion_engine import CompletionEngine
from taskmates.lib.context_.context_fork import context_fork
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.sdk.handlers.response_chunk_handler import ResponseChunkHandler
from taskmates.sdk.handlers.return_value_processor import ReturnValueProcessor
from taskmates.sdk.handlers.error_handler import ErrorHandler

@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    # TODO use completion_opts
    with temp_context(SIGNALS, Signals()) as signals:
        response_chunk_handler = ResponseChunkHandler()
        return_value_handler = ReturnValueProcessor()
        error_handler = ErrorHandler()

        sdk_handlers = [
            response_chunk_handler,
            return_value_handler,
            error_handler
        ]

        with signals.connected_to(sdk_handlers):
            with context_fork(CONTEXTS) as contexts:
                await CompletionEngine().perform_completion(
                    history=markdown,
                    incoming_messages=[],
                    contexts=contexts,
                    signals=signals)

        if error_handler.get_error():
            raise error_handler.get_error()

        return_value = return_value_handler.get_result()
        if return_value is not NOT_SET:
            return return_value["result"]

        return response_chunk_handler.get_result()
