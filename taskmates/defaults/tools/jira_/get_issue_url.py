import os

from jira import Issue


def get_issue_url(issue: Issue) -> str:
    """
    Get the URL of a JIRA issue.

    Args:
        issue (Issue): A JIRA issue.

    Returns:
        str: The URL of the JIRA issue.
    """
    return f"{os.environ['JIRA_SERVER']}/browse/{issue.key}"
