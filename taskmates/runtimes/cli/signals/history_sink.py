from pathlib import Path


class HistorySink:
    def __init__(self,
                 path: str | Path):
        super().__init__()
        self.path = path
        self.file = None

    async def process_chunk(self, sender, value):
        if sender == "history":
            return

        if self.file:
            self.file.write(value)
            self.file.flush()

    def __enter__(self):
        if self.path:
            self.file = open(self.path, "a")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
