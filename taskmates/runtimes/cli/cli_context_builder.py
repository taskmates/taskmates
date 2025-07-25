import os
from types import SimpleNamespace
from uuid import uuid4

from taskmates.core.workflow_engine.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.core.workflow_engine.run_context import RunContext


class CliContextBuilder(ContextBuilder):
    def __init__(self, args=None):
        self.args = args

    def build(self) -> RunContext:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["runner_environment"].update({
            "request_id": request_id,
            "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
            "cwd": os.getcwd(),
            "env": os.environ.copy(),
        })

        if hasattr(self.args, 'model') and self.args.model is not None:
            contexts["run_opts"]["model"] = self.args.model
        if hasattr(self.args, 'workflow') and self.args.workflow is not None:
            contexts["run_opts"]["workflow"] = self.args.workflow
        if hasattr(self.args, 'max_steps') and self.args.max_steps is not None:
            contexts["run_opts"]["max_steps"] = self.args.max_steps

        contexts["runner_config"]["interactive"] = False
        if hasattr(self.args, 'format') and self.args.format is not None:
            contexts["runner_config"]["format"] = self.args.format
        if hasattr(self.args, 'endpoint') and self.args.endpoint is not None:
            contexts["runner_config"]["endpoint"] = self.args.endpoint

        return contexts

def test_cli_context_builder():
    args = SimpleNamespace(model="test-model", max_steps=5, format="json",
                           endpoint="test-endpoint")
    builder = CliContextBuilder(args)
    contexts = builder.build()
    assert contexts["run_opts"]["model"] == "test-model"
    assert contexts["run_opts"]["max_steps"] == 5
    assert contexts["runner_config"]["format"] == "json"
    assert contexts["runner_config"]["endpoint"] == "test-endpoint"

# TODO
# def test_cli_context_builder_with_no_args():
#     args = SimpleNamespace()
#     builder = CliContextBuilder(args)
#     context = builder.build()
#     # assert context == ContextDefaults.build()
