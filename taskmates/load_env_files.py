import os

from dotenv import load_dotenv, find_dotenv


def load_env_files(environment=None):
    env_files = [
        '.env',
        '.env.local',
        f'.env.{environment}',
        f'.env.{environment}.local'
    ]

    # Remove .env.local for test environment
    if environment in ('test', 'integration_test'):
        env_files.remove('.env.local')

    # Reverse the list to give priority to files that come later
    for env_file in reversed(env_files):
        if dotenv_path := find_dotenv(env_file):
            load_dotenv(dotenv_path, override=True)

    # Load system environment variables last to give them highest priority
    for key, value in os.environ.items():
        os.environ[key] = value


def load_env_for_environment(environment):
    if environment not in ['development', 'test', 'production']:
        raise ValueError("Invalid environment. Choose 'development', 'test', or 'production'.")

    load_env_files(environment)

# Usage examples:
# For development:
# load_env_for_environment('development')

# For production:
# load_env_for_environment('production')

# For test:
# load_env_for_environment('test')
