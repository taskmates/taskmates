class Interrupted:
    def __init__(self):
        self._interrupted = False

    def get(self) -> bool:
        return self._interrupted

    def set(self, value: bool) -> None:
        self._interrupted = value
