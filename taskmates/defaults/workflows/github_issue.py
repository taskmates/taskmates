import os

import pytest

from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.cli_complete import CliComplete
from taskmates.extensions.actions.get_dotenv_values import get_dotenv_values
from taskmates.runner.actions.chat_templates.compose_chat_from_github_issue import compose_chat_from_github_issue
from taskmates.runner.actions.context_templates.set_up_github_token import set_up_github_token
from taskmates.runner.actions.inputs_templates.github_issue import fetch_github_issue


class GithubIssue(TaskmatesWorkflow):
    async def run(self,
                  repo_name: str,
                  issue_number: int,
                  response_format: str = 'text',
                  history_path: str = None
                  ):
        working_dir = "/Users/ralphus/Development/taskmates/taskmates"
        os.environ.update({"TASKMATES_ENV": "production"})
        env = get_dotenv_values(working_dir)
        os.environ.update(env)
        self.set_up_env()

        # job
        chat_content = self.github_issue_chat(issue_number, repo_name)

        # TODO: CHANGE CWD TO DEMO
        # job
        await CliComplete(contexts=self.execution_context.contexts).run(
            incoming_messages=[chat_content + "\n\nHey @demo_dev please have a look \n\n"],
            response_format="full",
            history_path=history_path)

    def set_up_env(self):
        cwd = os.getcwd()
        env = os.environ
        set_up_github_token(cwd, env)

    def github_issue_chat(self, issue_number, repo_name):
        inputs = fetch_github_issue(issue_number, repo_name)
        chat_content = compose_chat_from_github_issue(inputs)
        return chat_content


@pytest.mark.integration
async def test_github_issue(tmp_path):
    contexts = CliContextBuilder().build()
    await GithubIssue(contexts=contexts).run("taskmates/demo", 1, history_path=str(tmp_path / "history.md"))
