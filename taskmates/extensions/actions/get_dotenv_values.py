import os

from dotenv import dotenv_values


def get_dotenv_values(working_dir):
    env = {}
    taskmates_env = os.environ.get("TASKMATES_ENV", "production")
    dotenv_pats = [
        os.path.join(working_dir, ".env"),
        os.path.join(working_dir, ".env.local"),
        os.path.join(working_dir, ".env." + taskmates_env),
        os.path.join(working_dir, ".env." + taskmates_env + ".local"),
    ]
    for dotenv_path in dotenv_pats:
        if os.path.exists(dotenv_path):
            dotenv_vars = dotenv_values(str(dotenv_path))
            env.update(dotenv_vars)
    return env
