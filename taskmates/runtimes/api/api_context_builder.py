import os
from uuid import uuid4

import taskmates
from taskmates.core.workflow_engine.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.types import ApiRequest


class ApiContextBuilder(ContextBuilder):
    def __init__(self, payload: ApiRequest):
        self.payload = payload

    def build(self) -> RunContext:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["run_opts"]["workflow"] = "api_complete"
        contexts["runner_environment"].update(self.payload["runner_environment"].copy())
        contexts["runner_environment"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
        })

        contexts["run_opts"].update(self.payload["run_opts"].copy())

        contexts["runner_config"].update(dict(interactive=True,
                                              format="completion"))

        return contexts


def test_api_context_builder(tmp_path, context):
    payload: ApiRequest = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": "hello",
        "runner_environment": context["runner_environment"],
        "run_opts": {
            "model": "quote",
        },
    }
    builder = ApiContextBuilder(payload)
    context = builder.build()
    assert context["run_opts"]["model"] == "quote"
    assert context["runner_config"]["interactive"]
