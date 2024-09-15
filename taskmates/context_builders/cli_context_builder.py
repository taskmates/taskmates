import os
from types import SimpleNamespace
from uuid import uuid4

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.runner.contexts.contexts import Contexts


class CliContextBuilder(ContextBuilder):
    def __init__(self, args=None):
        self.args = args

    def build(self) -> Contexts:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["completion_context"].update({
            "request_id": request_id,
            "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
            "cwd": os.getcwd(),
            "env": os.environ.copy(),
        })

        if hasattr(self.args, 'model') and self.args.model is not None:
            contexts["completion_opts"]["model"] = self.args.model
        if hasattr(self.args, 'workflow') and self.args.workflow is not None:
            contexts["completion_opts"]["workflow"] = self.args.workflow
        if hasattr(self.args, 'max_steps') and self.args.max_steps is not None:
            contexts["completion_opts"]["max_steps"] = self.args.max_steps

        contexts["client_config"]["interactive"] = False
        if hasattr(self.args, 'format') and self.args.format is not None:
            contexts["client_config"]["format"] = self.args.format
        if hasattr(self.args, 'endpoint') and self.args.endpoint is not None:
            contexts["client_config"]["endpoint"] = self.args.endpoint

        return contexts

def test_cli_context_builder():
    args = SimpleNamespace(model="test-model", max_steps=5, format="json",
                           endpoint="test-endpoint")
    builder = CliContextBuilder(args)
    contexts = builder.build()
    assert contexts["completion_opts"]["model"] == "test-model"
    assert contexts["completion_opts"]["max_steps"] == 5
    assert contexts["client_config"]["format"] == "json"
    assert contexts["client_config"]["endpoint"] == "test-endpoint"

# TODO
# def test_cli_context_builder_with_no_args():
#     args = SimpleNamespace()
#     builder = CliContextBuilder(args)
#     contexts = builder.build()
#     # assert contexts == ContextDefaults.build()
