from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.cli_inputs_complete import CliInputsComplete
from taskmates.workflows.github_issue import GithubIssue
from taskmates.workflows.markdown_complete import MarkdownComplete

workflow_registry: dict[str, type[Workflow]] = {}


def initialize_registry(registry):
    registry["markdown_complete"] = MarkdownComplete
    registry["cli_inputs_complete"] = CliInputsComplete
    registry["github_issue"] = GithubIssue


initialize_registry(workflow_registry)
