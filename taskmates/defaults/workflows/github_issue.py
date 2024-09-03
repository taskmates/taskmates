import os

from taskmates.defaults.workflows.cli_complete import CliComplete
from taskmates.defaults.workflows.taskmates_workflow import TaskmatesWorkflow
from taskmates.runner.actions.chat_templates.compose_chat_from_github_issue import compose_chat_from_github_issue
from taskmates.runner.actions.context_templates.set_up_github_token import set_up_github_token
from taskmates.runner.actions.inputs_templates.github_issue import fetch_github_issue


class GithubIssue(TaskmatesWorkflow):
    async def run(self,
                  repo_name: str,
                  issue_number: int,
                  response_format: str = 'text',
                  history_path: str = None):
        self.set_up_env()

        # job
        chat_content = self.github_issue_chat(issue_number, repo_name)

        # job
        await CliComplete().run(incoming_messages=[chat_content],
                                response_format="full",
                                history_path="/tmp/history.md")

    def set_up_env(self):
        cwd = os.getcwd()
        env = os.environ
        set_up_github_token(cwd, env)

    def github_issue_chat(self, issue_number, repo_name):
        inputs = fetch_github_issue(issue_number, repo_name)
        chat_content = compose_chat_from_github_issue(inputs)
        return chat_content
