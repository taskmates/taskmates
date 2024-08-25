import time
from wrapt import wrap_function_wrapper

from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token
from taskmates.sdk import TaskmatesExtension


class GithubTokenEnvInjector(TaskmatesExtension):
    def __init__(self):
        super().__init__()
        self.token = None
        self.token_expiration = 0

    def get_token(self, env):
        current_time = time.time()
        installation_id = env['GITHUB_APP_INSTALLATION_ID']
        github_app_id = env['GITHUB_APP_ID']
        github_app_private_key = env['GITHUB_APP_PRIVATE_KEY']

        if self.token is None or current_time >= self.token_expiration:
            self.token = get_github_app_installation_token(
                github_app_id,
                github_app_private_key,
                installation_id
            )
            self.token_expiration = current_time + 3600  # GitHub tokens typically expire after 1 hour
        return self.token

    def aspect(self, wrapped, instance, args, kwargs):
        interpreter_env = CONTEXTS.get()["completion_context"]["env"]

        token = self.get_token(interpreter_env)
        interpreter_env["GITHUB_TOKEN"] = token
        interpreter_env["GH_TOKEN"] = token

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionCompletionProvider, 'perform_completion', self.aspect)
        wrap_function_wrapper(ToolExecutionCompletionProvider, 'perform_completion', self.aspect)
