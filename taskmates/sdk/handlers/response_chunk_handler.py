from taskmates.core.handlers.handler import Handler

class ResponseChunkHandler(Handler):
    def __init__(self):
        self.completion_chunks = []

    async def handle_response_chunk(self, chunk):
        self.completion_chunks.append(chunk)

    def connect(self, signals):
        signals.response.response.connect(self.handle_response_chunk)

    def disconnect(self, signals):
        signals.response.response.disconnect(self.handle_response_chunk)

    def get_result(self):
        return "".join(self.completion_chunks)
