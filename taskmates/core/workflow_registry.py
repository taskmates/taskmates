from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.cli_complete import CliComplete
from taskmates.defaults.workflows.github_issue import GithubIssue
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.defaults.workflows.sdk_complete import SdkComplete

workflow_registry: dict[str, type[TaskmatesWorkflow]] = {}


def initialize_registry(registry):
    registry["cli_complete"] = CliComplete
    registry["sdk_complete"] = SdkComplete
    registry["github_issue"] = GithubIssue
    # registry["api_complete"] = MarkdownComplete
    # registry["test_complete"] = MarkdownComplete
    # registry["markdown_complete"] = MarkdownComplete


initialize_registry(workflow_registry)
