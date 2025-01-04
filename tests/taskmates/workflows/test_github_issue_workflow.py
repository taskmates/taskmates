import pytest

from taskmates.workflow_engine.run import RUN
from taskmates.workflows.context_builders.test_context_builder import TestContextBuilder
from taskmates.workflows.github_issue import GithubIssue


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    contexts["run_opts"]["workflow"] = "github_issue"
    return contexts


@pytest.mark.integration
async def test_github_issue_workflow(tmp_path):
    run = RUN.get()
    run.objective.set_future_result("github_access_token_env", None, None)
    run.objective.set_future_result("github_issue_markdown_chat", None, "ISSUE_CHAT_CONTENT")
    result = await GithubIssue().fulfill(repo_name="taskmates/demo", issue_number=1)

    assert result == ('**demo_dev>** \n'
                      '> ISSUE_CHAT_CONTENT\n'
                      '> \n'
                      '> Hey @demo_dev please have a look \n'
                      '> \n'
                      '> \n'
                      '\n')
