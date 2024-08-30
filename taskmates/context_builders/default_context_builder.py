from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.contexts import Contexts


class DefaultContextBuilder(ContextBuilder):
    def build(self) -> Contexts:
        return {
            "client_config": {
                "taskmates_dirs": [],
            },
            "server_config": {},
            "completion_context": {},
            "step_context": {
                "current_step": 0,
            },
            "completion_opts": {
                "model": 'claude-3-5-sonnet-20240620',
                "template_params": {},
                "max_steps": 10000,
            },
        }


def test_default_context_builder():
    builder = DefaultContextBuilder()
    contexts = builder.build()
    assert isinstance(contexts, dict)
    assert "client_config" in contexts
    assert "completion_opts" in contexts
    assert contexts["completion_opts"]["model"] == 'claude-3-5-sonnet-20240620'
