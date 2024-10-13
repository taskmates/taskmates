from taskmates.runner.contexts.runner_context import RunnerContext


class ContextDefaults:
    @staticmethod
    def build() -> RunnerContext:
        return {
            "runner_config": {
                "taskmates_dirs": [],
            },
            "runner_environment": {},
            "run_opts": {
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
    assert "runner_config" in contexts
    assert "run_opts" in contexts
    assert contexts["run_opts"]["model"] == 'claude-3-5-sonnet-20240620'
