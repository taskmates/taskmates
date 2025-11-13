import json
import os

from wrapt import wrap_function_wrapper

from taskmates.core.workflow_engine.transactions.transaction import TRANSACTION
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_cell_execution_section_completion import \
    CodeCellExecutionSectionCompletion
from taskmates.core.workflows.markdown_completion.completions.tool_execution.tool_execution_section_completion import \
    ToolExecutionSectionCompletion
from taskmates.extensions.actions.get_github_app_installation_token import GithubAppInstallationToken
from taskmates.sdk import TaskmatesExtension


# @scope("app")
class GithubAppTokenEnvInjector(TaskmatesExtension):
    def handle(self, wrapped, instance, args, kwargs):
        runner_environment = TRANSACTION.get().context["runner_environment"]
        interpreter_env = runner_environment["env"]

        if "GITHUB_APP_INSTALLATION_ID" not in interpreter_env:
            return wrapped(*args, **kwargs)

        # Cache dir:
        cache_dir = runner_environment["cwd"] + "/.taskmates/tmp/cache"
        os.makedirs(cache_dir, exist_ok=True)
        cache_key = f"{cache_dir}/github_app_installation_token.json"

        if os.path.exists(cache_key):
            with open(cache_key, 'r') as f:
                token_response = json.load(f)
                github_app_installation_token = GithubAppInstallationToken(
                    interpreter_env['GITHUB_APP_ID'],
                    interpreter_env['GITHUB_APP_PRIVATE_KEY'],
                    interpreter_env['GITHUB_APP_INSTALLATION_ID'],
                    token_response['token'],
                    token_response['expiration']
                )
        else:
            github_app_installation_token = GithubAppInstallationToken(
                interpreter_env['GITHUB_APP_ID'],
                interpreter_env['GITHUB_APP_PRIVATE_KEY'],
                interpreter_env['GITHUB_APP_INSTALLATION_ID']
            )

        token_response = github_app_installation_token.get()
        with open(cache_key, 'w') as f:
            json.dump(token_response, f)

        token = token_response['token']

        interpreter_env["GITHUB_TOKEN"] = token
        interpreter_env["GH_TOKEN"] = token

        interpreter_env["GIT_AUTHOR_NAME"] = "Taskmates"
        interpreter_env["GIT_AUTHOR_EMAIL"] = "taskmates@users.noreply.github.com"

        result = wrapped(*args, **kwargs)
        return result

    def initialize(self):
        wrap_function_wrapper(CodeCellExecutionSectionCompletion, 'perform_completion', self.handle)
        wrap_function_wrapper(ToolExecutionSectionCompletion, 'perform_completion', self.handle)

# TODO
# def test_github_app_token_env_injector():
#     injector = GithubAppTokenEnvInjector()
#
#     test_context = {
#         "runner_environment": {
#             "env": {
#                 "GITHUB_APP_INSTALLATION_ID": "test_installation_id",
#                 "GITHUB_APP_ID": "test_app_id",
#                 "GITHUB_APP_PRIVATE_KEY": "test_private_key"
#             }
#         }
#     }
#
