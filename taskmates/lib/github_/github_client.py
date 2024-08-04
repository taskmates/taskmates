import base64
import os

import jwt
import requests
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from taskmates.lib.root_path.root_path import root_path


def github_client(app_id):
    load_dotenv(root_path() / '.env.production.local')
    private_key_data = base64.b64decode(os.environ['GITHUB_PRIVATE_KEY'])
    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None,
        backend=default_backend()
    )

    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + (10 * 60),
        'iss': app_id
    }

    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')

    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {encoded_jwt}',
        'Accept': 'application/vnd.github+json'
    })

    return session
