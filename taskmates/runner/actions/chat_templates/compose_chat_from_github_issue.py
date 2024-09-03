from typing import Dict

from jinja2 import Environment, FileSystemLoader

from taskmates.lib.root_path.root_path import root_path

template_dir = root_path() / "taskmates" / "defaults"
env = Environment(loader=FileSystemLoader(template_dir))


def compose_chat_from_github_issue(inputs: Dict[str, any]) -> str:
    template = env.get_template('ISSUE_COMMENT_TEMPLATE.jinja2')
    return template.render(**inputs)


def test_compose_issue_workflow_chat():
    inputs = {
        "issue_title": "Test Issue",
        "issue_number": 1,
        "issue_body": "Issue body",
        "comments": [
            {"body": "Comment 1", "user": {"login": "user1"}},
            {"body": "**user2>** Comment 2"},
        ]
    }

    chat = compose_chat_from_github_issue(inputs)

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
    inputs = {
        "issue_title": "Test Issue",
        "issue_number": 1,
        "issue_body": "Issue body",
        "comments": []
    }

    chat = compose_chat_from_github_issue(inputs)

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
