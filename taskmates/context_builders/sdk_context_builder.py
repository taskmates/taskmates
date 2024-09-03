import os
from uuid import uuid4

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.runner.contexts.contexts import Contexts
from taskmates.types import CompletionOpts


class SdkContextBuilder(ContextBuilder):
    def __init__(self, completion_opts: CompletionOpts):
        self.completion_opts = completion_opts

    def build(self) -> Contexts:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["completion_opts"]["workflow"] = "sdk_complete"
        contexts["completion_context"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
            "cwd": os.getcwd(),
        })

        contexts["completion_opts"].update(self.completion_opts.copy())

        contexts["client_config"].update({
            "interactive": True,
            "format": "completion",
        })

        return contexts


def test_sdk_context_builder():
    sdk_opts = {"model": "sdk-model", "max_steps": 3}
    builder = SdkContextBuilder(sdk_opts)
    contexts = builder.build()
    assert contexts["completion_opts"]["model"] == "sdk-model"
    assert contexts["completion_opts"]["max_steps"] == 3
    assert contexts["client_config"]["interactive"] == True
