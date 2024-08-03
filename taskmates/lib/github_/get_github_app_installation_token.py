import base64
import os

import jwt
import requests
import time
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from taskmates.lib.root_path.root_path import root_path

load_dotenv(root_path() / '.env.production.local')


def get_github_app_installation_token(installation_id):
    github_app_id = os.environ['GITHUB_APP_ID']
    github_private_key = os.environ['GITHUB_PRIVATE_KEY']
    private_key_data = base64.b64decode(github_private_key)
    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None,
    )
    payload = {
        'iat': int(time.time()) - 60,
        'exp': int(time.time()) + (10 * 60),
        'iss': github_app_id
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')

    headers = {
        'Authorization': f'Bearer {encoded_jwt}',
        'Accept': 'application/vnd.github+json'
    }
    response = requests.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers=headers
    )
    installation_token = response.json()['token']

    return installation_token
