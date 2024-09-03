from taskmates.runner.contexts.contexts import Contexts


class MaxStepsManager:
    def should_break(self, contexts: Contexts):
        return contexts['step_context']["current_step"] >= contexts['completion_opts']["max_steps"]
