import os
from uuid import uuid4

import taskmates
from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.contexts import Contexts
from taskmates.types import CompletionPayload


class ApiContextBuilder(ContextBuilder):
    def __init__(self, payload: CompletionPayload):
        self.payload = payload

    def build(self) -> Contexts:
        contexts = ContextDefaults().build()
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


def test_api_context_builder(tmp_path, contexts):
    payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": "hello",
        "completion_context": contexts["completion_context"],
        "completion_opts": {
            "model": "quote",
        },
    }
    builder = ApiContextBuilder(payload)
    contexts = builder.build()
    assert contexts["completion_opts"]["model"] == "quote"
    assert contexts["client_config"]["interactive"] == True
