import base64

import jwt
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def get_github_app_token(
        github_app_id,
        github_app_private_key
):
    private_key = serialization.load_pem_private_key(
        base64.b64decode(github_app_private_key),
        password=None,
        backend=default_backend()
    )
    payload = {
        'iat': int(time.time()) - 60,
        'exp': int(time.time()) + (10 * 60),
        'iss': int(github_app_id)
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    return encoded_jwt
