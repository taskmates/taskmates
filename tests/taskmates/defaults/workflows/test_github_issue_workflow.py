import pytest

from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.defaults.workflows.github_issue import GithubIssue


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    contexts["run_opts"]["workflow"] = "github_issue"
    return contexts


@pytest.mark.integration
async def test_github_issue_workflow(tmp_path, contexts):
    inputs = {"repo_name": "taskmates/demo", "issue_number": 1}

    workflow = GithubIssue(contexts=contexts)
    await workflow.run(**inputs)

    interesting_signals = ['incoming_message', 'input_formatting', 'error']
    filtered_signals = workflow.last_run["captured_signals"].filter_signals(interesting_signals)

    assert filtered_signals == [('history', 'Initial history\n'),
                                ('input_formatting', '\n'),
                                ('incoming_message', 'Incoming message'),
                                ('input_formatting', '\n\n')]
