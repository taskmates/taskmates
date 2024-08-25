from wrapt import wrap_function_wrapper

from taskmates.core.chat_session import ChatSession
from taskmates.sdk import TaskmatesExtension


# TODO
# FileSystemArtifactsSink()


class TaskmatesDevelopment(TaskmatesExtension):
    def aspect(self, wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(ChatSession, 'perform_step', self.aspect)
