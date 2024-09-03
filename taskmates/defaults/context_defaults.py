from taskmates.runner.contexts.contexts import Contexts


class ContextDefaults:
    @staticmethod
    def build() -> Contexts:
        return {
            "client_config": {
                "taskmates_dirs": [],
            },
            "server_config": {},
            "completion_context": {},
            "completion_opts": {
                "model": 'claude-3-5-sonnet-20240620',
                "inputs": {},
                "max_steps": 10000,
            },
            "step_context": {
                "current_step": 0,
            },
            "job_context": {},
        }


def test_default_context_builder():
    builder = ContextDefaults()
    contexts = builder.build()
    assert isinstance(contexts, dict)
    assert "client_config" in contexts
    assert "completion_opts" in contexts
    assert contexts["completion_opts"]["model"] == 'claude-3-5-sonnet-20240620'
