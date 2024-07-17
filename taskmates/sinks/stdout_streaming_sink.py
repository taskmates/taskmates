from taskmates.sinks.streaming_sink import StreamingSink


class StdoutStreamingSink(StreamingSink):
    def __init__(self):
        super().__init__()
        self.current_key = None

    async def process(self, token):
        if token is not None:
            print(token, end="", flush=True)
        else:
            print("")
