from taskmates.core.signal_receiver import SignalReceiver


class InterruptedOrKilledCollector(SignalReceiver):
    def __init__(self):
        self.interrupted_or_killed = False

    async def handle_interrupted(self, _sender):
        self.interrupted_or_killed = True

    async def handle_killed(self, _sender):
        self.interrupted_or_killed = True

    def connect(self, signals):
        signals.lifecycle.interrupted.connect(self.handle_interrupted)
        signals.lifecycle.killed.connect(self.handle_killed)

    def disconnect(self, signals):
        signals.lifecycle.interrupted.disconnect(self.handle_interrupted)
        signals.lifecycle.killed.disconnect(self.handle_killed)
