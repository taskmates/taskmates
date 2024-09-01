import os

import pytest
import time

from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token


class GithubAppInstallationToken:
    def __init__(self):
        self.token = None
        self.token_expiration = 0

    def get_token(self, github_app_id, github_app_private_key, installation_id):
        current_time = time.time()
        if self.token is None or current_time >= self.token_expiration:
            self.token = get_github_app_installation_token(
                github_app_id,
                github_app_private_key,
                installation_id
            )
            self.token_expiration = current_time + 3600  # GitHub tokens typically expire after 1 hour
        return self.token


@pytest.mark.integration
def test_github_app_installation_token():
    manager = GithubAppInstallationToken()

    github_app_id = os.environ['GITHUB_APP_ID']
    github_app_private_key = os.environ['GITHUB_APP_PRIVATE_KEY']
    installation_id = os.environ['GITHUB_APP_INSTALLATION_ID']

    # First call should get a new token
    token1 = manager.get_token(github_app_id, github_app_private_key, installation_id)
    assert token1 is not None

    # Second call within the hour should return the same token
    token2 = manager.get_token(github_app_id, github_app_private_key, installation_id)
    assert token2 == token1

    # Simulate token expiration
    manager.token_expiration = 0

    # This call should get a new token
    token3 = manager.get_token(github_app_id, github_app_private_key, installation_id)
    assert token3 is not None
    assert token3 != token1  # The token should be different after expiration
