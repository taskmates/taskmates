from taskmates.core.handlers.handler import Handler

class ErrorHandler(Handler):
    def __init__(self):
        self.error = None

    async def handle_error(self, payload):
        self.error = payload["error"]

    def connect(self, signals):
        signals.response.error.connect(self.handle_error)

    def disconnect(self, signals):
        signals.response.error.disconnect(self.handle_error)

    def get_error(self):
        return self.error
