from typing import Unpack

from typeguard import typechecked

from taskmates.cli.direct_completion import perform_direct_completion
from taskmates.config import CLIENT_CONFIG, COMPLETION_CONTEXT, CompletionOpts, COMPLETION_OPTS


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    completion_context = COMPLETION_CONTEXT.get()
    client_config = CLIENT_CONFIG.get()

    token = COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})
    try:
        if client_config.get("endpoint"):
            pass
            # TODO: rewrite this
            # return await perform_websocket_completion(markdown, completion_opts)
        else:
            return await perform_direct_completion(markdown, completion_context, client_config)
    finally:
        COMPLETION_OPTS.reset(token)
