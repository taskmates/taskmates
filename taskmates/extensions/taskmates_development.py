import aspectlib

from taskmates.core.chat_session import ChatSession
from taskmates.sdk import TaskmatesExtension


# TODO
# FileSystemArtifactsSink()


class TaskmatesDevelopment(TaskmatesExtension):
    @aspectlib.Aspect
    def aspect(self, callee, *args, **kwargs):
        result = yield aspectlib.Proceed
        yield aspectlib.Return(result)

    def initialize(self):
        # aspectlib.weave(CodeCellExecutionCompletionProvider.perform_completion, aspect)
        # aspectlib.weave(ToolExecutionCompletionProvider.perform_completion, aspect)

        # aspectlib.weave(ChatSession.handle_request, aspect)
        aspectlib.weave(ChatSession.perform_step, self.aspect)
