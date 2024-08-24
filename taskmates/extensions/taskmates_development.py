import aspectlib

from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.sdk import TaskmatesExtension


# TODO
# FileSystemArtifactsSink()


@aspectlib.Aspect
def aspect(completion_provider, *args, **kwargs):
    # TODO: problem:
    # if we use self.contexts,
    # we can't create a subcontext with augmented contexts
    #
    # self.context should probably be a property that pulls from CONTEXTS.get,
    # -> or we should get rid of it entirely
    #
    result = yield aspectlib.Proceed
    yield aspectlib.Return(result)


class TaskmatesDevelopment(TaskmatesExtension):
    def initialize(self):
        aspectlib.weave(CodeCellExecutionCompletionProvider.perform_completion, aspect)
        aspectlib.weave(ToolExecutionCompletionProvider.perform_completion, aspect)
        # aspectlib.weave(ChatCompletionProvider.perform_completion, aspect)
