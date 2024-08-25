import os

import aspectlib
from dotenv import dotenv_values

from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.sdk import TaskmatesExtension


class DotenvInjector(TaskmatesExtension):
    @aspectlib.Aspect
    def aspect(self, *args, **kwargs):
        taskmates_env = os.environ.get("TASKMATES_ENV", "production")
        contexts = CONTEXTS.get()
        interpreter_env = contexts["completion_context"]["env"]
        working_dir = contexts["completion_context"]["cwd"]

        dotenv_pats = [
            os.path.join(working_dir, ".env"),
            os.path.join(working_dir, ".env.local"),
            os.path.join(working_dir, ".env." + taskmates_env),
            os.path.join(working_dir, ".env." + taskmates_env + ".local"),
        ]

        for dotenv_path in dotenv_pats:
            if os.path.exists(dotenv_path):
                dotenv_vars = dotenv_values(dotenv_path)
                interpreter_env.update(dotenv_vars)

        yield aspectlib.Proceed

    def initialize(self):
        aspectlib.weave(CodeCellExecutionCompletionProvider.perform_completion, self.aspect)
        aspectlib.weave(ToolExecutionCompletionProvider.perform_completion, self.aspect)
