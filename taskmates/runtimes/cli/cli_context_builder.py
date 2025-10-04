import os
from types import SimpleNamespace
from uuid import uuid4

from taskmates.core.workflow_engine.context_builder import ContextBuilder
from taskmates.defaults.settings import Settings
from taskmates.core.workflow_engine.run_context import RunContext


class CliContextBuilder(ContextBuilder):
    def __init__(self, args=None):
        self.args = args

    def build(self) -> RunContext:
        context: RunContext = Settings().get()

        if hasattr(self.args, 'model') and self.args.model is not None:
            context["run_opts"]["model"] = self.args.model
        if hasattr(self.args, 'workflow') and self.args.workflow is not None:
            context["run_opts"]["workflow"] = self.args.workflow
        if hasattr(self.args, 'max_steps') and self.args.max_steps is not None:
            context["run_opts"]["max_steps"] = self.args.max_steps

        return context


def test_cli_context_builder():
    args = SimpleNamespace(model="test-model", max_steps=5, format="json",
                           endpoint="test-endpoint")
    builder = CliContextBuilder(args)
    contexts = builder.build()
    assert contexts["run_opts"]["model"] == "test-model"
    assert contexts["run_opts"]["max_steps"] == 5

# TODO
# def test_cli_context_builder_with_no_args():
#     args = SimpleNamespace()
#     builder = CliContextBuilder(args)
#     context = builder.build()
#     # assert context == ContextDefaults.build()
