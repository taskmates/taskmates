from taskmates.workflows.contexts.run_context import RunContext


class ContextDefaults:
    @staticmethod
    def build(run_opts=None) -> RunContext:
        default_run_opts = {
            "model": 'claude-3-7-sonnet-20250219',
            "max_steps": 10000,
        }
        run_opts = run_opts or default_run_opts
        return {
            "runner_config": {
                "taskmates_dirs": [],
            },
            "runner_environment": {},
            "run_opts": run_opts
        }


def test_default_context_builder():
    builder = ContextDefaults()
    contexts = builder.build()
    assert isinstance(contexts, dict)
    assert "runner_config" in contexts
    assert "run_opts" in contexts
    assert contexts["run_opts"]["model"] == 'claude-3-7-sonnet-20250219'
