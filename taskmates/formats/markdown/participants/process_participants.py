from pathlib import Path
from typing import Dict, Union

from typeguard import typechecked

from taskmates.environment.participants.load_participant_config import load_participant_config


@typechecked
async def process_participants(participants_configs: Dict[str, dict | None],
                               taskmates_dir: Union[str, Path]) -> dict[str, dict]:
    processed_participants = {}

    for participant_name, participant_config in participants_configs.items():
        participant_config = (participant_config or {}).copy()
        loaded_config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
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
    assert await process_participants(participants, taskmates_dir) == expected_output


async def test_process_participants_single_participant(tmp_path):
    participants = {"browser": {}}
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "browser.md").write_text("BROWSER_PROMPT\n")
    (taskmates_dir / "taskmates" / "browser.description.md").write_text("BROWSER_ROLE\n")

    result = await process_participants(participants, taskmates_dir)

    assert result['browser']['role'] == 'assistant'
    assert result['browser']['system'] == "BROWSER_PROMPT\n"
    assert result['browser']['description'] == "BROWSER_ROLE\n"


async def test_process_participants_multiple_assistants(tmp_path):
    participants = {
        "my_assistant_1": {},
        "my_assistant_2": {},
        "my_user": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "_introduction.md").write_text("THREAD_INTRODUCTION\n")
    (taskmates_dir / "taskmates" / "my_assistant_1.md").write_text("You are a helpful assistant 1.\n")
    (taskmates_dir / "taskmates" / "my_assistant_1.description.md").write_text("Assistant 1 role description\n")
    (taskmates_dir / "taskmates" / "my_assistant_2.md").write_text("You are a helpful assistant 2.\n")
    (taskmates_dir / "taskmates" / "my_assistant_2.description.md").write_text("Assistant 2 role description\n")
    (taskmates_dir / "taskmates" / "my_user.description.md").write_text("User role description\n")
    expected_output = {
        "my_assistant_1": {"role": "assistant",
                           "name": "my_assistant_1",
                           "system": "You are a helpful assistant 1.\n",
                           "description": "Assistant 1 role description\n"},
        "my_assistant_2": {"role": "assistant",
                           "name": "my_assistant_2",
                           "system": "You are a helpful assistant 2.\n",
                           "description": "Assistant 2 role description\n"},
        "my_user": {"role": "user",
                    "name": "my_user",
                    "description": "User role description\n"}
    }
    assert await process_participants(participants, taskmates_dir) == expected_output


async def test_process_participants_from_files(tmp_path):
    participants = {
        "my_assistant": {},
        "my_user": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "my_assistant.md").write_text("You are a helpful assistant.")
    (taskmates_dir / "taskmates" / "my_assistant.description.md").write_text("Assistant role description")
    (taskmates_dir / "taskmates" / "my_user.description.md").write_text("User role description")
    expected_output = {
        "my_assistant": {"role": "assistant", "name": "my_assistant", "system": "You are a helpful assistant.",
                         "description": "Assistant role description"},
        "my_user": {"role": "user", "name": "my_user", "description": "User role description"}
    }
    assert await process_participants(participants, taskmates_dir) == expected_output


async def test_multiple_participants_and_mediator(tmp_path):
    participants = {
        "browser": {},
        "coder": {}
    }
    taskmates_dir = tmp_path
    (taskmates_dir / "taskmates").mkdir()
    (taskmates_dir / "taskmates" / "_introduction.md").write_text("THREAD_INTRODUCTION\n")
    (taskmates_dir / "taskmates" / "mediator.md").write_text("MEDIATOR_ROLE\n")
    (taskmates_dir / "taskmates" / "browser.md").write_text("BROWSER_PROMPT\n")
    (taskmates_dir / "taskmates" / "browser.description.md").write_text("BROWSER_ROLE\n")
    (taskmates_dir / "taskmates" / "coder.md").write_text("CODER_PROMPT\n")
    (taskmates_dir / "taskmates" / "coder.description.md").write_text("CODER_ROLE\n")

    result = await process_participants(participants, taskmates_dir)

    assert result['browser']['role'] == 'assistant'
    assert result['browser']['system'] == "BROWSER_PROMPT\n"
    assert result['browser']['description'] == "BROWSER_ROLE\n"
    assert result['coder']['role'] == 'assistant'
    assert result['coder']['system'] == "CODER_PROMPT\n"
    assert result['coder']['description'] == "CODER_ROLE\n"
