import traceback

from blinker import Namespace


class BaseSignals:
    def __init__(self):
        self.namespace = Namespace()

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()


class ControlSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.interrupt_request = self.namespace.signal('interrupt_request')
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')


class OutputSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.start = self.namespace.signal('start')
        self.request = self.namespace.signal('request')
        self.formatting = self.namespace.signal('formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.success = self.namespace.signal('success')
        self.error = self.namespace.signal('error')
        self.finish = self.namespace.signal('finish')
        self.completion = self.namespace.signal('completion')
        self.artifact = self.namespace.signal('artifact')
        self.interrupted = self.namespace.signal('interrupted')
        self.killed = self.namespace.signal('killed')
        self.return_value = self.namespace.signal('return_value')
        self.next_responder = self.namespace.signal('next_responder')
        self.chat_completion = self.namespace.signal('chat_completion')
        self.code_cell_output = self.namespace.signal('code_cell_output')

        # Connect signals to completion
        self.formatting.connect(self.completion.send_async, weak=False)
        self.responder.connect(self.completion.send_async, weak=False)
        self.response.connect(self.completion.send_async, weak=False)
        self.next_responder.connect(self.completion.send_async, weak=False)

        async def send_error_completion(error):
            formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
            await self.completion.send_async(formatted)

        self.error.connect(send_error_completion, weak=False)
