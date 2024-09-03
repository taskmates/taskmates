from typing import List, Optional

import pytest

from taskmates.lib.github_.get_github_client import get_github_client

"""
This module contains functions for interacting with GitHub.

The corresponding unit tests are written in this file, not in a separate file.
"""


def create_issue(repo_name: str, title: str, body: str, labels: Optional[List[str]] = None) -> str:
    """
    Create a new GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        title (str): The title of the issue.
        body (str): The body (description) of the issue.
        labels (Optional[List[str]], optional): A list of labels to apply to the issue. Defaults to None.

    Returns:
        str: A formatted string containing the issue number and URL.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body, labels=labels)
    return f"Created issue #{issue.number} - {issue.html_url}"


def read_issue(repo_name: str, issue_number: int) -> str:
    """
    Fetch all details of a GitHub issue, including comments.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.

    Returns:
        str: A formatted string containing the issue details and comments.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    issue_details = f"Issue #{issue.number}\n"
    issue_details += f"Title: {issue.title}\n"
    issue_details += f"Body: {issue.body}\n"
    issue_details += f"State: {issue.state}\n"
    issue_details += f"Labels: {', '.join([label.name for label in issue.labels])}\n"
    issue_details += f"Assignee: {issue.assignee.login if issue.assignee else 'Unassigned'}\n"

    comments = issue.get_comments()
    if comments.totalCount > 0:
        issue_details += "Comments:\n"
        for comment in comments:
            issue_details += f"- {comment.user.login}: {comment.body}\n"
    else:
        issue_details += "Comments: None\n"

    return issue_details


def add_comment(repo_name: str, issue_number: int, comment: str) -> str:
    """
    Add a comment to a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.
        comment (str): The comment text.

    Returns:
        str: A formatted string containing the comment text and issue number.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    comment = issue.create_comment(comment)
    return f"Added comment to issue #{issue_number}: {comment.body}"


def update_issue_status(repo_name: str, issue_number: int, state: str) -> str:
    """
    Update the status of a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.
        state (str): The new state of the issue ('open' or 'closed').

    Returns:
        str: A formatted string containing the issue number and new state.

    Raises:
        ValueError: If the provided state is invalid.
    """
    if state not in ['open', 'closed']:
        raise ValueError(f"Invalid state: {state}. Must be 'open' or 'closed'.")

    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.edit(state=state)
    return f"Updated status of issue #{issue_number} to {state}"


def search_issues(repo_name: str, query: str) -> str:
    """
    Search for GitHub issues in a repository.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        query (str): The search query.

    Returns:
        str: A formatted string containing the list of matching issues, one issue per line.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issues = repo.get_issues(state='all', labels=[], sort='created', direction='desc')

    matching_issues = []
    for issue in issues:
        if query.lower() in issue.title.lower() or query.lower() in issue.body.lower():
            matching_issues.append(f"#{issue.number} - {issue.title} (State: {issue.state})")

    if not matching_issues:
        return "No matching issues found."

    return "Matching issues:\n" + "\n".join(matching_issues)


def close_issues(repo_name: str, issue_numbers: List[int]) -> str:
    """
    Close multiple GitHub issues.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_numbers (List[int]): A list of issue numbers to close.

    Returns:
        str: A formatted string containing the list of closed issues.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    closed_issues = []
    for issue_number in issue_numbers:
        issue = repo.get_issue(issue_number)
        issue.edit(state='closed')
        closed_issues.append(str(issue_number))
    return f"Closed issues: {', '.join(closed_issues)}"


@pytest.mark.integration
def test_create_issue():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue from pytest"
    body = "This is a test issue created from pytest"
    labels = ["test"]

    result = create_issue(repo_name, title, body, labels)

    assert "Created issue #" in result
    assert "https://github.com/taskmates/github-integration-testbed/issues/" in result

    # Clean up: close the created issue
    issue_number = int(result.split("#")[1].split(" ")[0])
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.edit(state="closed")


@pytest.mark.integration
def test_read_issue():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue for read_issue"
    body = "This is a test issue for the read_issue function"
    labels = ["test", "read"]

    create_result = create_issue(repo_name, title, body, labels)
    issue_number = int(create_result.split("#")[1].split(" ")[0])

    result = read_issue(repo_name, issue_number)

    assert f"Issue #{issue_number}" in result
    assert f"Title: {title}" in result
    assert f"Body: {body}" in result
    assert "State: open" in result
    assert "Labels: test, read" in result
    assert "Comments: None" in result

    # Clean up: close the created issue
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.edit(state="closed")


@pytest.mark.integration
def test_add_comment():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue for add_comment"
    body = "This is a test issue for the add_comment function"
    labels = ["test", "comment"]

    create_result = create_issue(repo_name, title, body, labels)
    issue_number = int(create_result.split("#")[1].split(" ")[0])

    comment_text = "This is a test comment"
    result = add_comment(repo_name, issue_number, comment_text)

    assert f"Added comment to issue #{issue_number}" in result
    assert comment_text in result

    # Verify the comment was added
    issue_details = read_issue(repo_name, issue_number)
    assert comment_text in issue_details

    # Clean up: close the created issue
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    issue.edit(state="closed")


@pytest.mark.integration
def test_update_issue_status():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue for update_issue_status"
    body = "This is a test issue for the update_issue_status function"
    labels = ["test", "status"]

    create_result = create_issue(repo_name, title, body, labels)
    issue_number = int(create_result.split("#")[1].split(" ")[0])

    result = update_issue_status(repo_name, issue_number, "closed")

    assert f"Updated status of issue #{issue_number} to closed" in result

    # Verify the status was updated
    issue_details = read_issue(repo_name, issue_number)
    assert "State: closed" in issue_details

    # Clean up is not needed as the issue is already closed


@pytest.mark.integration
def test_search_issues():
    repo_name = "taskmates/github-integration-testbed"
    title1 = "Test search issue 1"
    body1 = "This is a test issue for the search_issues function"
    title2 = "Test search issue 2"
    body2 = "Another test issue for searching"

    create_issue(repo_name, title1, body1, ["test", "search"])
    create_issue(repo_name, title2, body2, ["test", "search"])

    result = search_issues(repo_name, "test search issue")

    assert "Matching issues:" in result
    assert "Test search issue 1" in result
    assert "Test search issue 2" in result

    # Clean up: close all test issues
    github = get_github_client()
    repo = github.get_repo(repo_name)
    for issue in repo.get_issues(state='open', labels=['test', 'search']):
        issue.edit(state="closed")


@pytest.mark.integration
def test_close_issues():
    repo_name = "taskmates/github-integration-testbed"
    title1 = "Test close issue 1"
    title2 = "Test close issue 2"

    create_result1 = create_issue(repo_name, title1, "Test issue for closing", ["test", "close"])
    create_result2 = create_issue(repo_name, title2, "Another test issue for closing", ["test", "close"])

    issue_number1 = int(create_result1.split("#")[1].split(" ")[0])
    issue_number2 = int(create_result2.split("#")[1].split(" ")[0])

    result = close_issues(repo_name, [issue_number1, issue_number2])

    assert f"Closed issues: {issue_number1}, {issue_number2}" in result

    # Verify the issues were closed
    for issue_number in [issue_number1, issue_number2]:
        issue_details = read_issue(repo_name, issue_number)
        assert "State: closed" in issue_details

    # Clean up is not needed as the issues are already closed
