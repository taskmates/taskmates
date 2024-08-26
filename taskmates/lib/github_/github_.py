from typing import List, Optional, Dict, Any

import pytest
import time
from github import Issue, PullRequest, Commit, GithubException
from typeguard import typechecked

from taskmates.lib.github_.get_github_client import get_github_client

"""
This module contains functions for interacting with GitHub.

The corresponding unit tests are written in this file, not in a separate file.
"""


def create_issue(repo_name: str, title: str, body: str, labels: Optional[List[str]] = None) -> Issue:
    """
    Create a new GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        title (str): The title of the issue.
        body (str): The body (description) of the issue.
        labels (Optional[List[str]], optional): A list of labels to apply to the issue. Defaults to None.

    Returns:
        Issue: The created GitHub issue object.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    return repo.create_issue(title=title, body=body, labels=labels or [])


def read_issue(repo_name: str, issue_number: int) -> Issue:
    """
    Fetch a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.

    Returns:
        Issue: The GitHub issue object.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    return repo.get_issue(issue_number)


def add_comment(repo_name: str, issue_number: int, comment: str) -> Dict[str, Any]:
    """
    Add a comment to a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.
        comment (str): The comment text.

    Returns:
        Dict[str, Any]: A dictionary containing the comment details.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    comment = issue.create_comment(comment)
    return {
        "id": comment.id,
        "body": comment.body,
        "created_at": comment.created_at,
        "user": comment.user.login
    }


def update_issue_status(repo_name: str, issue_number: int, state: str) -> Issue:
    """
    Update the status of a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.
        state (str): The new state of the issue ('open' or 'closed').

    Returns:
        Issue: The updated GitHub issue object.

    Raises:
        ValueError: If the provided state is invalid.
    """
    if state not in ['open', 'closed']:
        raise ValueError(f"Invalid state: {state}. Must be 'open' or 'closed'.")

    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    return issue.edit(state=state)


def search_issues(repo_name: str, query: str) -> List[Issue]:
    """
    Search for GitHub issues in a repository.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        query (str): The search query.

    Returns:
        List[Issue]: A list of matching GitHub issue objects.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issues = repo.get_issues(state='all', labels=[], sort='created', direction='desc')

    return [issue for issue in issues if query.lower() in issue.title.lower() or query.lower() in issue.body.lower()]


@typechecked
def close_issues(repo_name: str, issue_numbers: List[int]) -> List[Issue]:
    """
    Close multiple GitHub issues.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_numbers (List[int]): A list of issue numbers to close.

    Returns:
        List[Issue]: A list of the successfully closed GitHub issue objects.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    closed_issues = []
    for issue_number in issue_numbers:
        issue = repo.get_issue(issue_number)
        if issue.state == 'closed':
            print(f"Issue {issue_number} is already closed.")
        else:
            issue.edit(state='closed')
            print(f"Successfully closed issue {issue_number}")
        closed_issues.append(issue)
    return closed_issues


def delete_all_comments(repo_name: str, issue_number: int) -> int:
    """
    Delete all comments from a GitHub issue.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        issue_number (int): The number of the issue.

    Returns:
        int: The number of comments deleted.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    comments = issue.get_comments()
    deleted_count = 0
    for comment in comments:
        comment.delete()
        deleted_count += 1
    return deleted_count


def wait_for_workflow_run(repo_name: str, branch: str, event_type: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Wait for a workflow run triggered by a specific event on a branch.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        branch (str): The name of the branch.
        event_type (str): The type of event that triggered the workflow (e.g., 'push', 'pull_request', 'issue_comment').
        timeout (int): Maximum time to wait for the workflow run in seconds. Defaults to 300 seconds (5 minutes).

    Returns:
        Dict[str, Any]: A dictionary containing the workflow run details, including status and output.

    Raises:
        TimeoutError: If the workflow doesn't complete within the specified timeout.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    start_time = time.time()

    while time.time() - start_time < timeout:
        workflow_runs = repo.get_workflow_runs(branch=branch, event=event_type)
        if workflow_runs.totalCount > 0:
            latest_run = workflow_runs[0]
            if latest_run.status == 'completed':
                return {
                    "id": latest_run.id,
                    "status": latest_run.status,
                    "conclusion": latest_run.conclusion,
                    "html_url": latest_run.html_url,
                    "logs_url": latest_run.logs_url
                }
        time.sleep(10)  # Wait for 10 seconds before checking again

    raise TimeoutError(f"Workflow run did not complete within {timeout} seconds")


def create_pull_request(repo_name: str, title: str, body: str, head: str, base: str) -> PullRequest:
    """
    Create a new pull request.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        title (str): The title of the pull request.
        body (str): The body (description) of the pull request.
        head (str): The name of the branch where your changes are implemented.
        base (str): The name of the branch you want the changes pulled into.

    Returns:
        PullRequest: The created GitHub pull request object.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)
    return repo.create_pull(title=title, body=body, head=head, base=base)


def commit_file(repo_name: str, file_path: str, commit_message: str, file_content: str, branch: str) -> Commit:
    """
    Commit a file to a branch.

    Args:
        repo_name (str): The name of the repository (e.g., "username/repo").
        file_path (str): The path to the file in the repository.
        commit_message (str): The commit message.
        file_content (str): The content of the file.
        branch (str): The name of the branch to commit to.

    Returns:
        Commit: The created GitHub commit object.
    """
    github = get_github_client()
    repo = github.get_repo(repo_name)

    try:
        # Try to get the file contents (file may already exist)
        contents = repo.get_contents(file_path, ref=branch)
        repo.update_file(contents.path, commit_message, file_content, contents.sha, branch=branch)
    except GithubException:
        # File doesn't exist, so create it
        repo.create_file(file_path, commit_message, file_content, branch=branch)

    # Get the latest commit on the branch
    return repo.get_branch(branch).commit


@pytest.mark.integration
def test_create_and_read_issue():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue from pytest"
    body = "This is a test issue created from pytest"
    labels = ["test"]

    issue = create_issue(repo_name, title, body, labels)
    assert issue.title == title
    assert issue.body == body
    assert [label.name for label in issue.labels] == labels

    read_issue_result = read_issue(repo_name, issue.number)
    assert read_issue_result.number == issue.number
    assert read_issue_result.title == title

    # Clean up
    update_issue_status(repo_name, issue.number, "closed")


@pytest.mark.integration
def test_add_and_delete_comments():
    repo_name = "taskmates/github-integration-testbed"
    title = "Test issue for comments"
    body = "This is a test issue for adding and deleting comments"
    issue = create_issue(repo_name, title, body)

    comment1 = add_comment(repo_name, issue.number, "Test comment 1")
    comment2 = add_comment(repo_name, issue.number, "Test comment 2")
    assert comment1["body"] == "Test comment 1"
    assert comment2["body"] == "Test comment 2"

    deleted_count = delete_all_comments(repo_name, issue.number)
    assert deleted_count == 2

    # Clean up
    update_issue_status(repo_name, issue.number, "closed")


@pytest.mark.integration
def test_search_and_close_issues():
    repo_name = "taskmates/github-integration-testbed"
    title_prefix = "Test search issue"
    issues = [
        create_issue(repo_name, f"{title_prefix} 1", "Test body 1"),
        create_issue(repo_name, f"{title_prefix} 2", "Test body 2")
    ]

    search_results = search_issues(repo_name, title_prefix)
    assert len(search_results) >= 2, f"Expected at least 2 search results, but got {len(search_results)}"

    issue_numbers = [issue.number for issue in issues]
    print(f"Attempting to close issues: {issue_numbers}")

    closed_issues = close_issues(repo_name, issue_numbers)
    assert len(closed_issues) == 2, f"Expected 2 closed issues, but got {len(closed_issues)}"

    for issue in closed_issues:
        assert issue.state == "closed", f"Issue {issue.number} is not closed"

    print("All issues closed successfully")


@pytest.mark.integration
def test_create_pull_request_and_commit_file():
    repo_name = "taskmates/github-integration-testbed"
    branch_name = "test-branch"
    file_path = "test_file.txt"
    file_content = "This is a test file"
    commit_message = "Add test file"

    # Create a new branch
    github = get_github_client()
    repo = github.get_repo(repo_name)
    source_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_branch.commit.sha)

    # Commit a file to the new branch
    commit = commit_file(repo_name, file_path, commit_message, file_content, branch_name)
    assert commit.commit.message == commit_message

    # Create a pull request
    pr_title = "Test Pull Request"
    pr_body = "This is a test pull request"
    pr = create_pull_request(repo_name, pr_title, pr_body, branch_name, "main")
    assert pr.title == pr_title
    assert pr.body == pr_body

    # Clean up (close the pull request and delete the branch)
    pr.edit(state="closed")
    repo.get_git_ref(f"heads/{branch_name}").delete()


@pytest.mark.integration
def test_wait_for_workflow_run():
    repo_name = "taskmates/github-integration-testbed"
    branch = "main"
    event_type = "push"

    # Create a simple workflow file
    workflow_content = """
name: Simple Workflow
on: [push]
jobs:
  simple_job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run a one-line script
        run: echo Hello, world!
    """

    commit_file(repo_name, ".github/workflows/simple_workflow.yml", "Add simple workflow", workflow_content, branch)

    # Wait a bit to ensure GitHub has time to register the new workflow
    time.sleep(10)

    # Trigger a workflow run
    commit_file(repo_name, "trigger_workflow.txt", "Trigger workflow", "Trigger content", branch)

    try:
        result = wait_for_workflow_run(repo_name, branch, event_type)
        assert result["status"] == "completed"
        assert "conclusion" in result
        assert "html_url" in result
        assert "logs_url" in result
    except TimeoutError:
        pytest.fail("Workflow run did not complete within the timeout period")

    # Clean up: remove the workflow file
    commit_file(repo_name, ".github/workflows/simple_workflow.yml", "Remove simple workflow", "", branch)
