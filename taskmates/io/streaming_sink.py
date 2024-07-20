from abc import ABC


class StreamingSink(ABC):
    async def process(self, token):
        raise NotImplementedError
