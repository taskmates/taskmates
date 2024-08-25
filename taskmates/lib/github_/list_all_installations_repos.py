import os

from dotenv import load_dotenv

from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token
from taskmates.lib.github_.get_github_app_token import get_github_app_token
from taskmates.lib.github_.get_github_session import get_github_session
from taskmates.lib.root_path.root_path import root_path

if __name__ == '__main__':
    load_dotenv(root_path() / '.env.local')

    app_session = get_github_session(get_github_app_token(
        os.environ['GITHUB_APP_ID'],
        os.environ['GITHUB_APP_PRIVATE_KEY']
    ))

    installations = app_session.get('https://api.github.com/app/installations').json()

    for installation in installations:
        installation_id = installation['id']
        installation_session = get_github_session(get_github_app_installation_token(
            os.environ['GITHUB_APP_ID'],
            os.environ['GITHUB_APP_PRIVATE_KEY'],
            installation_id,
        ))
        results = installation_session.get('https://api.github.com/installation/repositories').json()

        for repo in results['repositories']:
            print(repo['full_name'])
