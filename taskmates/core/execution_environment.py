import contextlib
import contextvars
import copy

from taskmates.core.processor import Processor
from taskmates.core.signals.signals_context import SignalsContext
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.runner.contexts.contexts import Contexts
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


class ExecutionEnvironment:
    def __init__(self,
                 contexts: Contexts,
                 processors: list[Processor] = None
                 ):
        self.parent: ExecutionEnvironment = EXECUTION_ENVIRONMENT.get(None)
        self.contexts: Contexts = copy.deepcopy(contexts)
        self.signals: SignalsContext = self.parent.signals if self.parent else SignalsContext()
        self.processors = processors or []

    @contextlib.contextmanager
    def context(self):
        TASKMATES_RUNTIME.get().initialize()
        with (temp_context(EXECUTION_ENVIRONMENT, self),
              stacked_contexts(self.processors)
              ):
            yield self


EXECUTION_ENVIRONMENT: contextvars.ContextVar[ExecutionEnvironment] = contextvars.ContextVar("execution_environment")
