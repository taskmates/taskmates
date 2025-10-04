import os
from uuid import uuid4

import taskmates
from taskmates.core.workflow_engine.context_builder import ContextBuilder
from taskmates.defaults.settings import Settings
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.types import ApiRequest


class ApiContextBuilder(ContextBuilder):
    def __init__(self, payload: ApiRequest):
        self.payload = payload

    def build(self) -> RunContext:
        context: RunContext = Settings().get()

        context["runner_environment"].update(self.payload["runner_environment"])
        context["run_opts"].update(self.payload["run_opts"])

        return context


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
