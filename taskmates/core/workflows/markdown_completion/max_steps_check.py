class MaxStepsCheck:
    def __init__(self, current_step, max_steps):
        self.current_step = current_step
        self.max_steps = max_steps

    def should_break(self):
        return self.current_step.get() > self.max_steps
