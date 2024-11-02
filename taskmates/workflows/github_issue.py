import os

from taskmates.workflows.markdown_complete import MarkdownComplete
from taskmates.extensions.actions.get_dotenv_values import get_dotenv_values
from taskmates.workflows.actions.chat_templates.compose_chat_from_github_issue import \
    compose_chat_from_github_issue
from taskmates.workflows.actions.context_templates.set_up_github_token import set_up_github_token
from taskmates.workflows.actions.inputs_templates.github_issue import fetch_github_issue
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.workflow import Workflow


@fulfills(outcome="github_issue_markdown_chat")
async def get_github_issue_markdown_chat(issue_number, repo_name):
    inputs = fetch_github_issue(issue_number, repo_name)
    chat_content = compose_chat_from_github_issue(inputs)
    return chat_content


@fulfills(outcome="set_github_token_env")
async def set_up_env():
    cwd = os.getcwd()
    env = os.environ
    set_up_github_token(cwd, env)

    working_dir = "/Users/ralphus/Development/taskmates/taskmates"
    os.environ.update({"TASKMATES_ENV": "production"})
    env = get_dotenv_values(working_dir)
    os.environ.update(env)


class GithubIssue(Workflow):
    async def steps(self,
                    repo_name: str,
                    issue_number: int,
                    response_format: str = 'text',
                    history_path: str = None
                    ):
        await set_up_env()

        markdown_chat = await get_github_issue_markdown_chat(issue_number, repo_name)

        # TODO: CHANGE CWD TO DEMO
        return await MarkdownComplete().fulfill(
            markdown_chat=markdown_chat + "\n\nHey @demo_dev please have a look \n\n")

# @pytest.mark.integration
# async def test_github_issue(tmp_path):
#     # TODO: use cli runner
#     contexts = CliContextBuilder().build()
#     await GithubIssue().fulfill(
#         repo_name="taskmates/demo",
#         issue_number=1,
#         history_path=str(tmp_path / "history.md"))
