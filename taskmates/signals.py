import contextvars
import traceback

import blinker
from blinker import Namespace


class Signals:
    namespace: Namespace
    chat_completion: blinker.Signal  # chat_completion_chunk
    response: blinker.Signal  # token
    code_cell_output: blinker.Signal
    start: blinker.Signal
    success: blinker.Signal
    error: blinker.Signal
    interrupt: blinker.Signal
    kill: blinker.Signal
    return_status:  blinker.Signal

    def __init__(self):
        self.namespace = Namespace()

        # control
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')

        # return status
        self.return_status = self.namespace.signal('return_status')

        # internal
        self.chat_completion = self.namespace.signal('chat_completion')
        self.code_cell_output = self.namespace.signal('code_cell_output')
        self.interrupted = self.namespace.signal('interrupted')

        # external
        self.start = self.namespace.signal('start')
        self.request = self.namespace.signal('request')
        self.formatting = self.namespace.signal('formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.success = self.namespace.signal('success')
        self.error = self.namespace.signal('error')
        self.finish = self.namespace.signal('finish')

        # extras
        self.next_responder = self.namespace.signal('next_responder')

        # derived
        self.completion = self.namespace.signal('completion')

        self.formatting.connect(self.completion.send_async, weak=False)
        self.responder.connect(self.completion.send_async, weak=False)
        self.response.connect(self.completion.send_async, weak=False)
        self.next_responder.connect(self.completion.send_async, weak=False)

        async def send_error_completion(e):
            formatted = f"**error** {str(e)}: {type(e).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
            await self.completion.send_async(formatted)

        self.error.connect(send_error_completion, weak=False)

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()


SIGNALS: contextvars.ContextVar['Signals'] = contextvars.ContextVar('signals')
