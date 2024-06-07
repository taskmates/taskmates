from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.completion_opts import CompletionOpts, CompletionOptsDefaults
from taskmates.cli.direct_completion import perform_direct_completion
from taskmates.cli.websocket_completion import perform_websocket_completion


@typechecked
async def async_complete(markdown, **completion_opts: Unpack[CompletionOpts]):
    completion_opts = {**CompletionOptsDefaults.get(), **completion_opts}

    if completion_opts.get("endpoint"):
        # TODO: review duplicate interrupt logic on perform_websocket_interaction
        return await perform_websocket_completion(markdown, completion_opts)
    else:
        return await perform_direct_completion(markdown, completion_opts)
