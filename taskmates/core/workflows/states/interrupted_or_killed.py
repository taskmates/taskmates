class InterruptedOrKilled:
    def __init__(self):
        self._interrupted_or_killed = False

    def get(self) -> bool:
        return self._interrupted_or_killed

    def set(self, value: bool) -> None:
        self._interrupted_or_killed = value
