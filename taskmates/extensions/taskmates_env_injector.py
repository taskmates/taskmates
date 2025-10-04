import os

from wrapt import wrap_function_wrapper

from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.workflows.markdown_completion.completions.tool_execution.tool_execution_completion_provider import \
    ToolExecutionCompletionProvider
from taskmates.sdk import TaskmatesExtension
from taskmates.core.workflow_engine.transaction import TRANSACTION


# @scope("app")
class TaskmatesEnvInjector(TaskmatesExtension):
    def handle(self, wrapped, instance, args, kwargs):
        runner_environment = TRANSACTION.get().execution_context.context["runner_environment"]

        # markdown_path = runner_environment["markdown_path"]
        # outcome_id = os.path.splitext(Path(markdown_path).name)[0]

        interpreter_env = runner_environment["env"]

        # Cache dir:
        cache_dir = runner_environment["cwd"] + "/.taskmates/tmp/cache"
        os.makedirs(cache_dir, exist_ok=True)

        # Notes path:
        notes_path = runner_environment["cwd"] + "/.taskmates/notes/notes.md"
        os.makedirs(os.path.dirname(notes_path), exist_ok=True)
        interpreter_env["TM_NOTES"] = notes_path

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionCompletionProvider, 'perform_completion', self.handle)
        wrap_function_wrapper(ToolExecutionCompletionProvider, 'perform_completion', self.handle)
