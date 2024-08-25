from taskmates.lib.github_.get_github_app_token import get_github_app_token
from taskmates.lib.github_.get_github_session import get_github_session


def get_github_app_installation_token(github_app_id,
                                      github_app_private_key,
                                      installation_id):
    session = get_github_session(
        get_github_app_token(
            github_app_id,
            github_app_private_key

        ))

    response = session.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens'
    )
    json = response.json()
    if 'token' not in json:
        raise ValueError(f"Failed to get installation token: {json}")
    installation_token = json['token']

    return installation_token
