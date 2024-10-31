from uuid import uuid4

from taskmates.workflows.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.workflows.contexts.context import Context


class TestContextBuilder(ContextBuilder):
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path

    def build(self, run_opts=None) -> Context:
        contexts = ContextDefaults().build(run_opts=run_opts)
        request_id = str(uuid4())

        contexts["runner_environment"].update({
            "request_id": request_id,
            "cwd": str(self.tmp_path),
            "env": {},
            "markdown_path": str(self.tmp_path / "chat.md"),
        })

        contexts["runner_config"].update({
            "interactive": False,
            "taskmates_dirs": [],
            "format": "completion"
        })

        return contexts