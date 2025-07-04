from taskmates.core.workflow_engine.workflow import Workflow
from taskmates.runtimes.cli.cli_complete import CliComplete
from taskmates.runtimes.github.github_issue import GithubIssue
from taskmates.core.workflows.markdown_completion.markdown_complete import MarkdownComplete

workflow_registry: dict[str, type[Workflow]] = {}


def initialize_registry(registry):
    registry["markdown_complete"] = MarkdownComplete
    registry["cli_complete"] = CliComplete
    registry["github_issue"] = GithubIssue


initialize_registry(workflow_registry)
