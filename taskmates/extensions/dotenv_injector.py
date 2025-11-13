from wrapt import wrap_function_wrapper

from taskmates.core.workflow_engine.transactions.transaction import TRANSACTION
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_cell_execution_section_completion import \
    CodeCellExecutionSectionCompletion
from taskmates.core.workflows.markdown_completion.completions.tool_execution.tool_execution_section_completion import \
    ToolExecutionSectionCompletion
from taskmates.extensions.actions.get_dotenv_values import get_dotenv_values
from taskmates.sdk import TaskmatesExtension


class DotenvInjector(TaskmatesExtension):
    def handle(self, wrapped, instance, args, kwargs):
        contexts = TRANSACTION.get().context
        interpreter_env = contexts["runner_environment"]["env"]
        working_dir = contexts["runner_environment"]["cwd"]

        env = get_dotenv_values(working_dir)

        interpreter_env.update(env)

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionSectionCompletion, 'perform_completion', self.handle)
        wrap_function_wrapper(ToolExecutionSectionCompletion, 'perform_completion', self.handle)
