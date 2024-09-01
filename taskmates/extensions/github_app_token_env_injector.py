from wrapt import wrap_function_wrapper

from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.extensions.actions.get_github_app_installation_token import GithubAppInstallationToken
from taskmates.sdk import TaskmatesExtension


class GithubAppTokenEnvInjector(TaskmatesExtension):
    def __init__(self):
        super().__init__()
        self.token_manager = GithubAppInstallationToken()

    def handle(self, wrapped, instance, args, kwargs):
        interpreter_env = CONTEXTS.get()["completion_context"]["env"]

        if "GITHUB_APP_INSTALLATION_ID" not in interpreter_env:
            return wrapped(*args, **kwargs)

        token = self.token_manager.get_token(
            interpreter_env['GITHUB_APP_ID'],
            interpreter_env['GITHUB_APP_PRIVATE_KEY'],
            interpreter_env['GITHUB_APP_INSTALLATION_ID']
        )
        interpreter_env["GITHUB_TOKEN"] = token
        interpreter_env["GH_TOKEN"] = token

        interpreter_env["GIT_AUTHOR_NAME"] = "Taskmates"
        interpreter_env["GIT_AUTHOR_EMAIL"] = "taskmates@users.noreply.github.com"

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionCompletionProvider, 'perform_completion', self.handle)
        wrap_function_wrapper(ToolExecutionCompletionProvider, 'perform_completion', self.handle)

# TODO
# def test_github_app_token_env_injector():
#     injector = GithubAppTokenEnvInjector()
#
#     test_context = {
#         "completion_context": {
#             "env": {
#                 "GITHUB_APP_INSTALLATION_ID": "test_installation_id",
#                 "GITHUB_APP_ID": "test_app_id",
#                 "GITHUB_APP_PRIVATE_KEY": "test_private_key"
#             }
#         }
#     }
#
