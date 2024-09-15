from taskmates.defaults.workflows.cli_complete import CliComplete
from taskmates.defaults.workflows.github_issue import GithubIssue
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.core.taskmates_workflow import TaskmatesWorkflow

workflow_registry: dict[str, type[TaskmatesWorkflow]] = {}


def initialize_registry(function_registry):
    function_registry["cli_complete"] = CliComplete
    function_registry["api_complete"] = MarkdownComplete
    function_registry["sdk_complete"] = MarkdownComplete
    function_registry["test_complete"] = MarkdownComplete
    function_registry["markdown_complete"] = MarkdownComplete
    function_registry["github_issue"] = GithubIssue


initialize_registry(workflow_registry)
