import os
from uuid import uuid4

import taskmates
from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.runner.contexts.runner_context import RunnerContext
from taskmates.types import ApiRequest


class ApiContextBuilder(ContextBuilder):
    def __init__(self, payload: ApiRequest):
        self.payload = payload

    def build(self) -> RunnerContext:
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


def test_api_context_builder(tmp_path, contexts):
    payload: ApiRequest = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": "hello",
        "runner_environment": contexts["runner_environment"],
        "run_opts": {
            "model": "quote",
        },
    }
    builder = ApiContextBuilder(payload)
    contexts = builder.build()
    assert contexts["run_opts"]["model"] == "quote"
    assert contexts["runner_config"]["interactive"] == True
