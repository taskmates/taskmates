import os
from uuid import uuid4

from taskmates.workflows.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.workflows.contexts.run_context import RunContext
from taskmates.types import RunOpts


class SdkContextBuilder(ContextBuilder):
    def __init__(self, run_opts: RunOpts):
        self.run_opts = run_opts

    def build(self) -> RunContext:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["run_opts"]["workflow"] = "sdk_complete"
        contexts["runner_environment"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
            "cwd": os.getcwd(),
            "markdown_path": "<function>",
        })

        contexts["run_opts"].update(self.run_opts.copy())

        contexts["runner_config"].update({
            "interactive": False,
            "format": "text"
        })

        return contexts


def test_sdk_context_builder():
    sdk_opts = {"model": "quote", "max_steps": 3}
    builder = SdkContextBuilder(sdk_opts)
    contexts = builder.build()
    assert contexts["run_opts"]["model"] == "quote"
    assert contexts["run_opts"]["max_steps"] == 3
    assert contexts["runner_config"]["interactive"] is False
