from taskmates.lib.github_ import github_


def fetch_github_issue(issue_number, repo_name):
    issue = github_.read_issue(repo_name, issue_number)
    comments = github_.get_issue_comments(repo_name, issue_number)
    inputs = {
        "issue_title": issue.title,
        "issue_number": issue_number,
        "issue_body": issue.body,
        "comments": comments
    }
    return inputs
