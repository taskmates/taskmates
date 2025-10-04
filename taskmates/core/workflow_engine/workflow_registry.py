from taskmates.core.workflow_engine.workflow import Workflow
from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
from taskmates.runtimes.github.github_issue import GithubIssue

workflow_registry: dict[str, type[Workflow]] = {}


def initialize_registry(registry):
    registry["markdown_complete"] = MarkdownCompletion
    registry["github_issue"] = GithubIssue


initialize_registry(workflow_registry)
