from wrapt import wrap_function_wrapper

from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.get_dotenv_values import get_dotenv_values
from taskmates.sdk import TaskmatesExtension


class DotenvInjector(TaskmatesExtension):
    def wraper(self, wrapped, instance, args, kwargs):
        contexts = CONTEXTS.get()
        interpreter_env = contexts["completion_context"]["env"]
        working_dir = contexts["completion_context"]["cwd"]

        env = get_dotenv_values(working_dir)

        interpreter_env.update(env)

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionCompletionProvider, 'perform_completion', self.wraper)
        wrap_function_wrapper(ToolExecutionCompletionProvider, 'perform_completion', self.wraper)
