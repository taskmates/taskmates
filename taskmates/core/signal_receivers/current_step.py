class CurrentStep:
    def __init__(self):
        self.current_step = 0

    def get(self):
        return self.current_step

    def increment(self):
        self.current_step += 1
