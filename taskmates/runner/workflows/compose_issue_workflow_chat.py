import os
from typing import List

from jinja2 import Environment, FileSystemLoader

template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'defaults')
env = Environment(loader=FileSystemLoader(template_dir))


def compose_issue_workflow_chat(issue_title: str, issue_number: int, issue_body: str, comments: List[dict]) -> str:
    template = env.get_template('ISSUE_COMMENT_TEMPLATE.jinja2')
    return template.render(
        issue_title=issue_title,
        issue_number=issue_number,
        issue_body=issue_body,
        comments=comments
    )


def test_compose_issue_workflow_chat():
    issue_title = "Test Issue"
    issue_number = 1
    issue_body = "Issue body"
    comments = [
        {"body": "Comment 1", "user": {"login": "user1"}},
        {"body": "**user2>** Comment 2"},
    ]

    chat = compose_issue_workflow_chat(issue_title, issue_number, issue_body, comments)

    assert chat == ('**github>**\n'
                    '\n'
                    'Please address the request on the Issue below.\n'
                    '\n'
                    'The source code of the appropriate branch is already checked out and '
                    'available in the current working directory.\n'
                    '\n'
                    'Issue: Test Issue #1\n'
                    '\n'
                    'Issue body\n'
                    '\n'
                    '\n'
                    '\n'
                    '\n'
                    '**user1>** Comment 1\n'
                    '\n'
                    '\n'
                    '\n'
                    '**user2>** Comment 2\n'
                    '\n'
                    '\n')


def test_compose_chat_no_comments():
    issue_title = "Test Issue"
    issue_number = 1
    issue_body = "Issue body"
    comments = []

    chat = compose_issue_workflow_chat(issue_title, issue_number, issue_body, comments)

    assert chat == ('**github>**\n'
                    '\n'
                    'Please address the request on the Issue below.\n'
                    '\n'
                    'The source code of the appropriate branch is already checked out and '
                    'available in the current working directory.\n'
                    '\n'
                    'Issue: Test Issue #1\n'
                    '\n'
                    'Issue body\n'
                    '\n')
