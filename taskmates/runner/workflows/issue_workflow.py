import os

import sys

from taskmates.extensions.actions.get_dotenv_values import get_dotenv_values
from taskmates.extensions.actions.get_github_app_installation_token import GithubAppInstallationToken
from taskmates.lib.github_ import github_
from taskmates.runner.workflows.compose_issue_workflow_chat import compose_issue_workflow_chat
from taskmates.runner.workflows.parse_issue_url import parse_issue_url
from taskmates.taskmates_runtime import TaskmatesRuntime


def run_workflow(repo_name: str,
                 issue_number: int,
                 workspace_dir: str,
                 markdown_chat_path: str) -> str:
    TaskmatesRuntime.initialize()

    env_extras = get_dotenv_values(os.getcwd())
    os.environ.update(env_extras)

    token_response = GithubAppInstallationToken(
        os.environ['GITHUB_APP_ID'],
        os.environ['GITHUB_APP_PRIVATE_KEY'],
        os.environ['GITHUB_APP_INSTALLATION_ID']
    ).get()

    os.environ["GITHUB_ACCESS_TOKEN"] = token_response['token']

    issue = github_.read_issue(repo_name, issue_number)
    comments = github_.get_issue_comments(repo_name, issue_number)

    template_params = {
        "issue_title": issue.title,
        "issue_number": issue_number,
        "issue_body": issue.body,
        "comments": comments
    }

    chat_content = compose_issue_workflow_chat(template_params)

    # TODO: outputs
    # os.makedirs(os.path.dirname(markdown_chat_path), exist_ok=True)
    # with open(markdown_chat_path, 'w') as f:
    #     f.write(chat_content)

    # TODO: run
    # Simulating the taskmates complete command
    # response = f"Processed issue {issue_number} for repository {repo_name}"
    print(chat_content)

    # TODO: outputs

    # os.makedirs(workspace_dir, exist_ok=True)
    # with open(f"{workspace_dir}/response.md", 'w') as f:
    #     f.write(response)
    #
    # with open(markdown_chat_path, 'w') as f:
    #     f.write(response)
    #
    # return response


def main():
    # TODO: check subclass wrapping
    # TODO: generate github app token inside get_dotenv_values -> as a context builder
    # TODO: rename get_dotenv_values to get_values
    # TODO: move it into env.py
    # TODO: rename it to taskmates_runtime or something like that
    os.environ.update(get_dotenv_values(os.getcwd()))

    if len(sys.argv) != 2:
        print("Usage: python issue_workflow.py <issue_url>", file=sys.stderr)
        sys.exit(1)

    repo_name, issue_number = parse_issue_url(sys.argv[1])
    runner_temp = os.environ.get('RUNNER_TEMP', '/tmp')
    markdown_chat_path = os.environ.get('MARKDOWN_CHAT_PATH', f"{runner_temp}/chat.md")

    response = run_workflow(repo_name, issue_number, runner_temp, markdown_chat_path)
    print(response)


if __name__ == "__main__":
    main()
