import requests


def get_github_session(encoded_jwt):
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {encoded_jwt}',
        'Accept': 'application/vnd.github+json'
    })

    return session
