from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.cli_complete import CliComplete
from taskmates.defaults.workflows.github_issue import GithubIssue
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete

workflow_registry: dict[str, type[TaskmatesWorkflow]] = {}


def initialize_registry(registry):
    registry["markdown_complete"] = MarkdownComplete
    registry["cli_complete"] = CliComplete
    registry["github_issue"] = GithubIssue


initialize_registry(workflow_registry)
