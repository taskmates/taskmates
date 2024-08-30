import os
from types import SimpleNamespace
from uuid import uuid4

from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.context_builders.default_context_builder import DefaultContextBuilder
from taskmates.contexts import Contexts


class CliContextBuilder(ContextBuilder):
    def __init__(self, args):
        self.args = args

    def build(self) -> Contexts:
        contexts = DefaultContextBuilder().build()
        request_id = str(uuid4())

        contexts["completion_context"].update({
            "request_id": request_id,
            "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
            "cwd": os.getcwd(),
            "env": os.environ.copy(),
        })

        contexts["completion_opts"].update({
            "model": self.args.model if hasattr(self.args, 'model') else None,
            "template_params": merge_template_params(self.args.template_params) if hasattr(self.args,
                                                                                           'template_params') else {},
            "max_steps": self.args.max_steps if hasattr(self.args, 'max_steps') else None,
        })

        contexts["client_config"].update({
            "interactive": False,
            "format": self.args.format if hasattr(self.args, 'format') else None,
            "endpoint": self.args.endpoint if hasattr(self.args, 'endpoint') else None
        })

        return contexts


def test_cli_context_builder():
    args = SimpleNamespace(model="test-model", template_params=[{"key1": "value1"}], max_steps=5, format="json",
                           endpoint="test-endpoint")
    builder = CliContextBuilder(args)
    contexts = builder.build()
    assert contexts["completion_opts"]["model"] == "test-model"
    assert contexts["completion_opts"]["max_steps"] == 5
    assert contexts["client_config"]["format"] == "json"
    assert contexts["client_config"]["endpoint"] == "test-endpoint"
