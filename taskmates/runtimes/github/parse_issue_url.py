from typing import Tuple
from urllib.parse import urlparse


def parse_issue_url(url: str) -> Tuple[str, int]:
    parsed = urlparse(url)
    path_parts = parsed.path.split('/')
    repo_owner = path_parts[1]
    repo_name = path_parts[2]
    issue_number = int(path_parts[4])
    return f"{repo_owner}/{repo_name}", issue_number


def test_parse_issue_url():
    url = "https://github.com/taskmates/github-integration-testbed/issues/1"
    repo_name, issue_number = parse_issue_url(url)
    assert repo_name == "taskmates/github-integration-testbed"
    assert issue_number == 1
