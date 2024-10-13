from taskmates.runner.contexts.runner_context import RunnerContext


class MaxStepsCheck:
    def should_break(self, contexts: RunnerContext):
        return contexts['step_context']["current_step"] >= contexts['run_opts']["max_steps"]
