from taskmates.workflows.contexts.context import Context


class ContextDefaults:
    @staticmethod
    def build(run_opts=None) -> Context:
        default_run_opts = {
            "model": 'claude-3-5-sonnet-20241022',
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
    assert contexts["run_opts"]["model"] == 'claude-3-5-sonnet-20241022'
