from uuid import uuid4

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.defaults.context_defaults import ContextDefaults
from taskmates.runner.contexts.contexts import Contexts


class TestContextBuilder(ContextBuilder):
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path

    def build(self) -> Contexts:
        contexts = ContextDefaults().build()
        request_id = str(uuid4())

        contexts["completion_context"].update({
            "request_id": request_id,
            "cwd": str(self.tmp_path),
            "env": {},
            "markdown_path": str(self.tmp_path / "chat.md"),
        })

        contexts["completion_opts"].update({
            "model": "quote",
            "inputs": {},
            "max_steps": 1,
            "workflow": "test_complete"
        })

        contexts["client_config"].update({
            "interactive": False,
            "taskmates_dirs": [],
        })

        return contexts


def test_test_context_builder(tmp_path):
    contexts = TestContextBuilder(tmp_path).build()

    assert "completion_context" in contexts
    assert "completion_opts" in contexts
    assert "client_config" in contexts

    assert contexts["completion_context"]["cwd"] == str(tmp_path)
    assert contexts["completion_context"]["markdown_path"] == str(tmp_path / "chat.md")

    assert contexts["completion_opts"]["model"] == "quote"
    assert contexts["completion_opts"]["max_steps"] == 1

    assert contexts["client_config"]["interactive"] is False
