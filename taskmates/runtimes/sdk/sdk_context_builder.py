import os
from uuid import uuid4

from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.types import RunOpts
from taskmates.core.workflow_engine.context_builder import ContextBuilder
from taskmates.core.workflow_engine.run_context import RunContext


class SdkContextBuilder(ContextBuilder):
    def __init__(self, run_opts: RunOpts):
        self.run_opts = run_opts

    def build(self) -> RunContext:
        context: RunContext = ContextDefaults().build()
        request_id = str(uuid4())

        context["run_opts"]["workflow"] = "sdk_complete"
        context["runner_environment"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
            "cwd": os.getcwd(),
            "markdown_path": "<function>",
        })

        context["run_opts"].update(self.run_opts.copy())

        context["runner_config"].update({
            "interactive": False,
            "format": "text"
        })

        return context


def test_sdk_context_builder():
    sdk_opts = {"model": "quote", "max_steps": 3}
    builder = SdkContextBuilder(sdk_opts)
    contexts = builder.build()
    assert contexts["run_opts"]["model"] == "quote"
    assert contexts["run_opts"]["max_steps"] == 3
    assert contexts["runner_config"]["interactive"] is False
