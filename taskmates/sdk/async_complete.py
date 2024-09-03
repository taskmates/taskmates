from typing import Unpack

from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.core.runner import Runner
from taskmates.core.signals import Signals
from taskmates.sdk.handlers.return_value_handler import ReturnValueHandler
from taskmates.types import CompletionOpts


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    return_value_handler = ReturnValueHandler()

    contexts = SdkContextBuilder(completion_opts).build()
    handlers = [return_value_handler]
    with Signals().connected_to(handlers):
        await Runner().run(
            inputs=dict(
                history=markdown,
                incoming_messages=[],
            ),
            contexts=contexts,
        )

    return return_value_handler.get_return_value()
