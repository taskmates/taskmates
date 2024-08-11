from taskmates.lib.github_.get_github_app_token import get_github_app_token
from taskmates.lib.github_.get_github_session import get_github_session


def get_github_app_installation_token(installation_id):
    session = get_github_session(get_github_app_token())

    response = session.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    )
    installation_token = response.json()['token']

    return installation_token
