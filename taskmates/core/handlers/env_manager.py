from taskmates.core.handlers.handler import Handler
from taskmates.contexts import CONTEXTS

class EnvManager(Handler):
    async def handle_before_step(self, _sender):
        contexts = CONTEXTS.get()

    def connect(self, signals):
        signals.lifecycle.before_step.connect(self.handle_before_step)

    def disconnect(self, signals):
        signals.lifecycle.before_step.disconnect(self.handle_before_step)
