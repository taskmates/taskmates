import os

from github import Github


def get_github_client() -> Github:
    """
    Returns a GitHub client using the access token stored in the GITHUB_ACCESS_TOKEN environment variable.

    Returns:
        Github: An authenticated GitHub client.

    Raises:
        ValueError: If the GITHUB_ACCESS_TOKEN environment variable is not set.
    """
    access_token = os.environ.get('GITHUB_ACCESS_TOKEN')
    if not access_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set")

    return Github(access_token)


# Test the function
if __name__ == "__main__":
    try:
        client = get_github_client()
        print(f"Successfully created GitHub client. User: {client.get_user().login}")
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
