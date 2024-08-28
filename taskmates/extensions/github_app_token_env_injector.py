import time
from wrapt import wrap_function_wrapper

from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token
from taskmates.sdk import TaskmatesExtension


class GithubAppTokenEnvInjector(TaskmatesExtension):
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

    def wraper(self, wrapped, instance, args, kwargs):
        interpreter_env = CONTEXTS.get()["completion_context"]["env"]

        if "GITHUB_APP_INSTALLATION_ID" not in interpreter_env:
            return wrapped(*args, **kwargs)

        token = self.get_token(interpreter_env)
        interpreter_env["GITHUB_TOKEN"] = token
        interpreter_env["GH_TOKEN"] = token

        interpreter_env["GIT_AUTHOR_NAME"] = "Taskmates"
        interpreter_env["GIT_AUTHOR_EMAIL"] = "taskmates@users.noreply.github.com"

        # TODO
        # https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables
        # GIT_AUTHOR_NAME is the human-readable name in the “author” field.
        # GIT_AUTHOR_EMAIL is the email for the “author” field.
        # GIT_AUTHOR_DATE is the timestamp used for the “author” field.
        # GIT_COMMITTER_NAME sets the human name for the “committer” field.
        # GIT_COMMITTER_EMAIL is the email address for the “committer” field.
        # GIT_COMMITTER_DATE is used for the timestamp in the “committer” field.

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionCompletionProvider, 'perform_completion', self.wraper)
        wrap_function_wrapper(ToolExecutionCompletionProvider, 'perform_completion', self.wraper)
