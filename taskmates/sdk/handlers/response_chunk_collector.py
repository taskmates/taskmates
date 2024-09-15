from taskmates.core.processor import Processor
from taskmates.core.execution_environment import EXECUTION_ENVIRONMENT


class ResponseChunkCollector(Processor):
    def __init__(self):
        self.completion_chunks = []

    async def handle_response_chunk(self, chunk):
        self.completion_chunks.append(chunk)

    def __enter__(self):
        signals = EXECUTION_ENVIRONMENT.get().signals
        signals.response.response.connect(self.handle_response_chunk)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_ENVIRONMENT.get().signals
        signals.response.response.disconnect(self.handle_response_chunk)

    def get_result(self):
        return "".join(self.completion_chunks)
