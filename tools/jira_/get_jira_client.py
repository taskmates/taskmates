import os

from jira import JIRA


def get_jira_client() -> JIRA:
    """
    Get a JIRA client instance using environment variables for authentication.

    Returns:
        JIRA: A JIRA client instance.
    """
    email = os.environ['JIRA_USER']
    server = os.environ['JIRA_SERVER']
    api_token = os.environ['JIRA_API_KEY']
    return JIRA(server=server, basic_auth=(email, api_token))
