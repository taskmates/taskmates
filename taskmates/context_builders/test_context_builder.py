from uuid import uuid4

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.runner.contexts.runner_context import RunnerContext


class TestContextBuilder(ContextBuilder):
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path

    def build(self) -> RunnerContext:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["runner_environment"].update({
            "request_id": request_id,
            "cwd": str(self.tmp_path),
            "env": {},
            "markdown_path": str(self.tmp_path / "chat.md"),
        })

        contexts["run_opts"].update({
            "model": "quote",
            "inputs": {},
            "max_steps": 1,
            "workflow": "test_complete",
        })

        contexts["runner_config"].update({
            "interactive": False,
            "taskmates_dirs": [],
            "format": "completion"
        })

        return contexts


def test_test_context_builder(tmp_path):
    contexts = TestContextBuilder(tmp_path).build()

    assert "runner_environment" in contexts
    assert "run_opts" in contexts
    assert "runner_config" in contexts

    assert contexts["runner_environment"]["cwd"] == str(tmp_path)
    assert contexts["runner_environment"]["markdown_path"] == str(tmp_path / "chat.md")

    assert contexts["run_opts"]["model"] == "quote"
    assert contexts["run_opts"]["max_steps"] == 1

    assert contexts["runner_config"]["interactive"] is False
