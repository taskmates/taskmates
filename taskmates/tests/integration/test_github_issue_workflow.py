import pytest

from taskmates.lib.github_ import github_

# TODO
# @pytest.mark.integration
# def test_run_workflow(tmp_path):
#     # Create a test issue
#     repo_name = "taskmates/github-integration-testbed"
#     issue = github_.create_issue(repo_name, "Test issue for process_issue", "This is a test issue body")
#     github_.add_comment(repo_name, issue.number, "Test comment for process_issue")
#
#     # Process the issue
#     runner_temp = str(tmp_path / "runner_temp")
#     markdown_chat_path = str(tmp_path / "chat.md")
#     response = run_workflow(repo_name, issue.number, runner_temp, markdown_chat_path)
#
#     assert f"Processed issue {issue.number} for repository {repo_name}" in response
#
#     # Check if files were created
#     assert (tmp_path / "runner_temp" / "response.md").exists()
#     assert (tmp_path / "chat.md").exists()
#
#     # Clean up
#     github_.update_issue_status(repo_name, issue.number, "closed")
