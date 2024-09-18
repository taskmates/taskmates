import contextlib
import contextvars
import copy

from taskmates.core.processor import Processor
from taskmates.core.signals.signals_context import SignalsContext
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.runner.contexts.contexts import Contexts
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


class ExecutionContext:
    def __init__(self,
                 contexts: Contexts = None,
                 signals: SignalsContext = None,
                 processors: list[Processor] = None
                 ):
        self.parent: ExecutionContext = EXECUTION_CONTEXT.get(None)

        self.contexts: Contexts = contexts or (copy.deepcopy(self.parent.contexts) if self.parent else {})
        if self.contexts == {}:
            raise ValueError("Contexts must be provided")
        self.signals: SignalsContext = signals or (self.parent.signals if self.parent else SignalsContext())
        self.processors = processors or []

    @contextlib.contextmanager
    def context(self):
        TASKMATES_RUNTIME.get().initialize()
        with (temp_context(EXECUTION_CONTEXT, self),
              stacked_contexts(self.processors)
              ):
            yield self


EXECUTION_CONTEXT: contextvars.ContextVar[ExecutionContext] = contextvars.ContextVar("execution_context")
