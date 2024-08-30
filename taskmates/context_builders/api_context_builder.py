import os
from uuid import uuid4

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.context_builders.default_context_builder import DefaultContextBuilder
from taskmates.contexts import Contexts
from taskmates.types import CompletionPayload


class ApiContextBuilder(ContextBuilder):
    def __init__(self, payload: CompletionPayload):
        self.payload = payload

    def build(self) -> Contexts:
        contexts = DefaultContextBuilder().build()
        request_id = str(uuid4())

        contexts["completion_context"].update(self.payload["completion_context"].copy())
        contexts["completion_context"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
        })

        contexts["completion_opts"].update(self.payload["completion_opts"].copy())

        contexts["client_config"].update(dict(interactive=True,
                                              format="completion"))

        return contexts


def test_api_context_builder():
    payload = {
        "completion_context": {"test_key": "test_value"},
        "completion_opts": {"model": "api-model"}
    }
    builder = ApiContextBuilder(payload)
    contexts = builder.build()
    assert contexts["completion_context"]["test_key"] == "test_value"
    assert contexts["completion_opts"]["model"] == "api-model"
    assert contexts["client_config"]["interactive"] == True
