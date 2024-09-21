from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT


class ResponseChunkCollector(Job):
    def __init__(self):
        self.completion_chunks = []

    async def handle_response_chunk(self, chunk):
        self.completion_chunks.append(chunk)

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.response.connect(self.handle_response_chunk)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.response.disconnect(self.handle_response_chunk)

    def get_result(self):
        return "".join(self.completion_chunks)
