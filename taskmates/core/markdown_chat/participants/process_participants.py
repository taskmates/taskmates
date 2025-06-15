from pathlib import Path
from typing import Dict, Union

from typeguard import typechecked

from taskmates.config.load_participant_config import load_participant_config


@typechecked
async def process_participants(participants_configs: Dict[str, dict | None],
                               taskmates_dirs: list[Union[str, Path]]) -> dict[str, dict]:
    processed_participants = {}

    for participant_name, participant_config in participants_configs.items():
        participant_config = (participant_config or {}).copy()
        loaded_config = await load_participant_config(participants_configs, participant_name, taskmates_dirs)
        participant_config.update(loaded_config)
        processed_participants[participant_name] = participant_config

    return processed_participants


async def test_process_participants_configs(tmp_path):
    participants = {
        "my_assistant": {"role": "assistant", "system": "You are a helpful assistant."},
        "my_user": {"role": "user", "description": "You are a user asking for help."}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    expected_output = {
        "my_assistant": {"role": "assistant", "name": "my_assistant", "system": "You are a helpful assistant."},
        "my_user": {"role": "user", "name": "my_user", "description": "You are a user asking for help."}
    }
    assert await process_participants(participants, [taskmates_dir]) == expected_output


async def test_process_participants_single_participant(tmp_path):
    participants = {"browser": {}}
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "browser.md").write_text("""---
description: BROWSER_ROLE
---
BROWSER_PROMPT
""")

    result = await process_participants(participants, [taskmates_dir])

    assert result['browser']['role'] == 'assistant'
    assert result['browser']['system'] == "BROWSER_PROMPT\n"
    assert result['browser']['description'] == "BROWSER_ROLE"


async def test_process_participants_multiple_assistants(tmp_path):
    participants = {
        "my_assistant_1": {},
        "my_assistant_2": {},
        "my_user": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "engine").mkdir()
    (taskmates_dir / "engine" / "chat_introduction.md").write_text("THREAD_INTRODUCTION\n")
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "my_assistant_1.md").write_text("""---
description: Assistant 1 role description
---
You are a helpful assistant 1.
""")
    (taskmates_dir / "taskmates" / "my_assistant_2.md").write_text("""---
description: Assistant 2 role description
---
You are a helpful assistant 2.
""")
    (taskmates_dir / "taskmates" / "my_user.md").write_text("""---
description: User role description
role: user
---
""")
    expected_output = {
        "my_assistant_1": {"role": "assistant",
                           "name": "my_assistant_1",
                           "system": "You are a helpful assistant 1.\n",
                           "description": "Assistant 1 role description"},
        "my_assistant_2": {"role": "assistant",
                           "name": "my_assistant_2",
                           "system": "You are a helpful assistant 2.\n",
                           "description": "Assistant 2 role description"},
        "my_user": {"role": "user",
                    "name": "my_user",
                    "description": "User role description",
                    "system": ""}
    }
    assert await process_participants(participants, [taskmates_dir]) == expected_output


async def test_process_participants_from_files(tmp_path):
    participants = {
        "my_assistant": {},
        "my_user": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "my_assistant.md").write_text("""---
description: Assistant role description
---
You are a helpful assistant.""")
    (taskmates_dir / "taskmates" / "my_user.md").write_text("""---
description: User role description
role: user
---
""")
    expected_output = {
        "my_assistant": {"role": "assistant", "name": "my_assistant", "system": "You are a helpful assistant.",
                         "description": "Assistant role description"},
        "my_user": {"role": "user", "name": "my_user", "description": "User role description", "system": ""}
    }
    assert await process_participants(participants, [taskmates_dir]) == expected_output


async def test_multiple_participants_and_mediator(tmp_path):
    participants = {
        "browser": {},
        "coder": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "engine").mkdir()
    (taskmates_dir / "engine" / "chat_introduction.md").write_text("THREAD_INTRODUCTION\n")
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "mediator.md").write_text("MEDIATOR_ROLE\n")
    (taskmates_dir / "taskmates" / "browser.md").write_text("""---
description: BROWSER_ROLE
---
BROWSER_PROMPT
""")
    (taskmates_dir / "taskmates" / "coder.md").write_text("""---
description: CODER_ROLE
---
CODER_PROMPT
""")

    result = await process_participants(participants, [taskmates_dir])

    assert result['browser']['role'] == 'assistant'
    assert result['browser']['system'] == "BROWSER_PROMPT\n"
    assert result['browser']['description'] == "BROWSER_ROLE"
    assert result['coder']['role'] == 'assistant'
    assert result['coder']['system'] == "CODER_PROMPT\n"
    assert result['coder']['description'] == "CODER_ROLE"
