from typing import Unpack

from typeguard import typechecked

from taskmates.config.completion_opts import CompletionOpts
from taskmates.context_builders.build_sdk_context import build_sdk_context
from taskmates.core.completion_engine import CompletionEngine
from taskmates.lib.context_.temp_context import temp_context
from taskmates.sdk.handlers.return_value_handler import ReturnValueHandler
from taskmates.signals.signals import SIGNALS, Signals


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    return_value_handler = ReturnValueHandler()

    with temp_context(SIGNALS, Signals()) as signals, \
            signals.connected_to([return_value_handler]), \
            build_sdk_context(completion_opts) as contexts:
        await CompletionEngine().perform_completion(
            history=markdown,
            incoming_messages=[],
            contexts=contexts,
            signals=signals,
            states={})

    return return_value_handler.get_return_value()
