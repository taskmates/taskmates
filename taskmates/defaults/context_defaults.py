from taskmates.contexts import Contexts


class ContextDefaults:
    @staticmethod
    def build() -> Contexts:
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
    builder = ContextDefaults()
    contexts = builder.build()
    assert isinstance(contexts, dict)
    assert "client_config" in contexts
    assert "completion_opts" in contexts
    assert contexts["completion_opts"]["model"] == 'claude-3-5-sonnet-20240620'
