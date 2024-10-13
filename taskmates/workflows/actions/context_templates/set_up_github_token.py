import os

from taskmates.extensions.actions.get_dotenv_values import get_dotenv_values
from taskmates.extensions.actions.get_github_app_installation_token import GithubAppInstallationToken


def set_up_github_token(cwd, env):
    env_extras = get_dotenv_values(cwd)

    env.update(env_extras)
    token_response = GithubAppInstallationToken(
        env['GITHUB_APP_ID'],
        env['GITHUB_APP_PRIVATE_KEY'],
        env['GITHUB_APP_INSTALLATION_ID']
    ).get()
    env["GITHUB_ACCESS_TOKEN"] = token_response['token']
