import os
import requests
from dotenv import load_dotenv
from taskmates.lib.root_path.root_path import root_path
from taskmates.lib.github_.github_client import github_client
from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token

load_dotenv(root_path() / '.env.production.local')

app_id = os.environ['GITHUB_APP_ID']
client = github_client(app_id)

installations = client.get('https://api.github.com/app/installations').json()

for installation in installations:
    installation_id = installation['id']
    access_token = get_github_app_installation_token(installation_id)

    installation_client = requests.Session()
    installation_client.headers.update({'Authorization': f'Bearer {access_token}'})

    results = installation_client.get('https://api.github.com/installation/repositories').json()

    for repo in results['repositories']:
        print(repo['full_name'])
