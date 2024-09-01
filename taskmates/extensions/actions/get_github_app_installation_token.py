import os

import pytest
import time

from taskmates.lib.github_.get_github_app_installation_token import get_github_app_installation_token


# @scope("app")
class GithubAppInstallationToken:
    def __init__(self, github_app_id, github_app_private_key, installation_id, token=None, expiration=0):
        self.github_app_id = github_app_id
        self.github_app_private_key = github_app_private_key
        self.installation_id = installation_id
        self.token = token
        self.token_expiration = expiration

    def get(self):
        current_time = time.time()
        if self.token is None or current_time >= self.token_expiration:
            self.token = get_github_app_installation_token(
                self.github_app_id,
                self.github_app_private_key,
                self.installation_id
            )
            self.token_expiration = current_time + 3600  # GitHub tokens typically expire after 1 hour
        return {
            'token': self.token,
            'expiration': self.token_expiration
        }


@pytest.mark.integration
def test_github_app_installation_token():
    github_app_id = os.environ['GITHUB_APP_ID']
    github_app_private_key = os.environ['GITHUB_APP_PRIVATE_KEY']
    installation_id = os.environ['GITHUB_APP_INSTALLATION_ID']

    manager = GithubAppInstallationToken(github_app_id, github_app_private_key, installation_id)

    # First call should get a new token
    result1 = manager.get()
    assert isinstance(result1, dict)
    assert 'token' in result1 and 'expiration' in result1
    assert result1['token'] is not None
    assert result1['expiration'] > time.time()

    # Second call within the hour should return the same token and expiration
    result2 = manager.get()
    assert result2 == result1

    # Simulate token expiration
    manager.token_expiration = 0

    # This call should get a new token
    result3 = manager.get()
    assert isinstance(result3, dict)
    assert 'token' in result3 and 'expiration' in result3
    assert result3['token'] is not None
    assert result3['token'] != result1['token']  # The token should be different after expiration
    assert result3['expiration'] > result1['expiration']  # The new expiration should be later than the old one
