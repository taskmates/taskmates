from taskmates.core.daemon import Daemon
from taskmates.core.run import RUN
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class InterruptedOrKilled(Daemon):
    def __init__(self):
        super().__init__()
        self.interrupted_or_killed = False

    def get(self):
        return self.interrupted_or_killed

    async def handle_interrupted(self, _sender):
        self.interrupted_or_killed = True

    async def handle_killed(self, _sender):
        self.interrupted_or_killed = True

    def __enter__(self):
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.status.interrupted.connected_to(self.handle_interrupted),
            run.status.killed.connected_to(self.handle_killed)
        ]))
