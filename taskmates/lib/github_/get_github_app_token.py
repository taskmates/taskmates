import base64
import os

import jwt
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from taskmates.lib.root_path.root_path import root_path


def get_github_app_token():
    github_app_id = os.environ['GITHUB_APP_ID']
    github_app_private_key = base64.b64decode(os.environ['GITHUB_APP_PRIVATE_KEY'])
    private_key = serialization.load_pem_private_key(
        github_app_private_key,
        password=None,
        backend=default_backend()
    )
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + (10 * 60),
        'iss': github_app_id
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt
