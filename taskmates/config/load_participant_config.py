import os
import time
from pathlib import Path

import pytest
from typeguard import typechecked

from taskmates.config.find_config_file import find_config_file
from taskmates.config.get_file_mtime import get_file_mtime
from taskmates.core.markdown_chat.parse_front_matter_and_messages import parse_front_matter_and_messages
from taskmates.defaults.settings import Settings

load_cache = {}


@typechecked
def load_participant_config(participants_configs: dict, participant_name: str) -> dict:
    taskmates_dirs = Settings.get()["runner_environment"]["taskmates_dirs"]

    participants_configs_dirs = []

    for config_dir in taskmates_dirs:
        config_dir = Path(config_dir)
        participants_configs_dirs.append(config_dir / "taskmates")
        participants_configs_dirs.append(config_dir / "private")

    participant_md_path = find_config_file(f"{participant_name}.md", participants_configs_dirs)

    current_mtimes = {
        "md": get_file_mtime(participant_md_path),
    }

    cache_key = (participant_name, tuple(str(d) for d in participants_configs_dirs))
    if cache_key in load_cache:
        cached_config, cached_mtimes = load_cache[cache_key]
        if all(current_mtimes[key] == cached_mtimes[key] for key in current_mtimes):
            return cached_config.copy()  # Return a copy to prevent modifying the cached version
        elif any(current_mtimes[key] is None for key in current_mtimes):
            # If any file is missing, remove the cache entry
            del load_cache[cache_key]

    updated_participant_config = (participants_configs.get(participant_name) or {}).copy()
    updated_participant_config["name"] = participant_name

    # process system, description, and model from frontmatter
    if participant_md_path and participant_md_path.exists():
        content = participant_md_path.read_text()
        front_matter, messages = parse_front_matter_and_messages(content, participant_md_path, implicit_role="system")
        if len(messages) != 1:
            raise ValueError("Multi-messages taskmate definitions not supported yet")

        updated_participant_config["system"] = messages[0]["content"]
        updated_participant_config.update(front_matter)

    # compute default role
    if "role" not in updated_participant_config:
        if (participant_name == "assistant" or
                "system" in updated_participant_config or
                "tools" in updated_participant_config):
            updated_participant_config["role"] = "assistant"
        else:
            updated_participant_config["role"] = "user"

    if (participant_name not in ("user", "assistant", "cell_output") and
            updated_participant_config["role"] != "user" and
            "system" not in updated_participant_config):
        raise ValueError(f"Participant @{participant_name} not found")

    load_cache[cache_key] = (updated_participant_config.copy(), current_mtimes)
    return updated_participant_config


@pytest.fixture
def sample_data(tmp_path, transaction):
    participants_configs = {
        "assistant1": {"role": "assistant", "system": "existing system info"}
    }
    participant_name = "assistant1"
    taskmates_config_dir1 = tmp_path / ".taskmates" / "taskmates"
    taskmates_config_dir1.mkdir(parents=True)

    (taskmates_config_dir1 / f"{participant_name}.md").write_text("""---
role: assistant
description: Description of assistant1
model: gpt-4o-mini
---
System message
""")

    yield participants_configs, participant_name, [tmp_path / ".taskmates"]


def test_load_participant_config(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    config = load_participant_config(participants_configs, participant_name)

    assert config["name"] == participant_name
    assert config["role"] == "assistant"
    assert config["system"] == "System message\n"
    assert config["description"] == "Description of assistant1"
    assert config["model"] == "gpt-4o-mini"


def test_load_participant_config_missing_fields(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    # Modify the file to remove some fields
    config_file = taskmates_dirs[0] / "taskmates" / f"{participant_name}.md"
    config_file.write_text("""\
System message
""")

    config = load_participant_config(participants_configs, participant_name)

    assert config["name"] == participant_name
    assert config["role"] == "assistant"
    assert config["system"] == "System message\n"
    assert "description" not in config
    assert "model" not in config


def test_load_participant_config_caching(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    # Load config for the first time
    config1 = load_participant_config(participants_configs, participant_name)

    # Modify the file
    config_file = taskmates_dirs[0] / "taskmates" / f"{participant_name}.md"
    config_file.write_text("""---
role: assistant
description: Updated description
model: gpt-4o-mini
---
System message
""")

    # Ensure the modification time is different
    time.sleep(0.01)
    os.utime(config_file, None)

    # Load config again (should detect the change and not use cache)
    config2 = load_participant_config(participants_configs, participant_name)

    assert config1 != config2
    assert config2["description"] == "Updated description"

    # Load config once more (should use cache)
    config3 = load_participant_config(participants_configs, participant_name)

    assert config2 == config3
    assert config3["description"] == "Updated description"

# TODO
# def test_load_participant_config_multiple_dirs(sample_data):
#     participants_configs, participant_name, taskmates_dirs = sample_data
#
#     # Create a file in the second directory
#     config_dir2 = taskmates_dirs[0] / "taskmates2"
#     config_dir2.mkdir(parents=True)
#     (config_dir2 / f"{participant_name}.md").write_text("""---
# role: assistant
# model: gpt-4
# ---
# System message
# """)
#
#     config = load_participant_config(participants_configs, participant_name)
#
#     assert config["model"] == "gpt-4o-mini"  # Should use the file from the first directory
#
#     # Remove the file from the first directory
#     os.remove(taskmates_dirs[0] / "taskmates" / f"{participant_name}.md")
#
#     load_cache.clear()
#     config = load_participant_config(participants_configs, participant_name)
#
#     assert config["model"] == "gpt-4"  # Should now use the file from the second directory
