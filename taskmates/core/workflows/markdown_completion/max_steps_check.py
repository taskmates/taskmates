from taskmates.core.workflow_engine.run import RUN


class MaxStepsCheck:
    def should_break(self):
        run = RUN.get()
        return run.state["current_step"].get() > run.context['run_opts']["max_steps"]
