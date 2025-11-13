class CurrentStep:
    def __init__(self):
        super().__init__()
        self.current_step = 1

    def get(self):
        return self.current_step

    def increment(self):
        self.current_step += 1

    def set(self, value: int):
        self.current_step = value

    def __str__(self):
        return str(self.current_step)

    def __repr__(self):
        return str(self.current_step)
