from taskmates.contexts import Contexts


def build_default_contexts() -> Contexts:
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
