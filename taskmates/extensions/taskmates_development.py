import aspectlib

from taskmates.core.chat_completion.chat_completion_provider import ChatCompletionProvider
from taskmates.sdk import TaskmatesExtension


# TODO
# FileSystemArtifactsSink()


@aspectlib.Aspect
def aspect(completion_provider, *args, **kwargs):
    result = yield aspectlib.Proceed
    yield aspectlib.Return(result)


class TaskmatesDevelopment(TaskmatesExtension):
    def initialize(self):
        print("TaskmatesDevelopment initialized")
        aspectlib.weave(ChatCompletionProvider.perform_completion, aspect)
        # aspectlib.weave(CompletionProvider.perform_completion, aspect)
