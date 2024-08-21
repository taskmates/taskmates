import os
from pathlib import Path
from typing import Union, List

import pytest
import time
import yaml
from typeguard import typechecked

from taskmates.config.find_config_file import find_config_file
from taskmates.formats.markdown.parsing.parse_front_matter_and_messages import parse_front_matter_and_messages

load_cache = {}


def load_yaml_config(config_path: Path) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


@typechecked
async def load_participant_config(participants_configs: dict,
                                  participant_name: str,
                                  taskmates_dirs: List[Union[str, Path]]) -> dict:
    def get_file_mtime(file_path):
        return os.path.getmtime(file_path) if file_path and os.path.exists(file_path) else None

    taskmates_definition_dirs = []

    for config_dir in taskmates_dirs:
        if isinstance(config_dir, str):
            config_dir = Path(config_dir)
        taskmates_definition_dirs.append(config_dir / "taskmates")
        taskmates_definition_dirs.append(config_dir / "private")

    participant_md_path = find_config_file(f"{participant_name}.md", taskmates_definition_dirs)

    current_mtimes = {
        "md": get_file_mtime(participant_md_path),
    }

    cache_key = (participant_name, tuple(str(d) for d in taskmates_definition_dirs))
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
        messages, front_matter = await parse_front_matter_and_messages(participant_md_path, content, "system")
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
def sample_data(tmp_path):
    participants_configs = {
        "assistant1": {"role": "assistant", "system": "existing system info"}
    }
    participant_name = "assistant1"
    taskmates_config_dir1 = tmp_path / "opt" / "taskmates1"
    taskmates_config_dir2 = tmp_path / "opt" / "taskmates2"
    taskmates_config_dir1.mkdir(parents=True)
    taskmates_config_dir2.mkdir(parents=True)

    # Create sample participant file with all metadata in frontmatter
    taskmates_dir1 = taskmates_config_dir1 / "taskmates"
    taskmates_dir1.mkdir(parents=True)
    (taskmates_dir1 / f"{participant_name}.md").write_text("""---
role: assistant
description: Description of assistant1
model: gpt-3.5-turbo
---
System message
""")

    yield participants_configs, participant_name, [taskmates_config_dir1, taskmates_config_dir2]


@pytest.mark.asyncio
async def test_load_participant_config(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    config = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config["name"] == participant_name
    assert config["role"] == "assistant"
    assert config["system"] == "System message\n"
    assert config["description"] == "Description of assistant1"
    assert config["model"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_load_participant_config_missing_fields(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    # Modify the file to remove some fields
    config_file = taskmates_dirs[0] / "taskmates" / f"{participant_name}.md"
    config_file.write_text("""\
System message
""")

    config = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config["name"] == participant_name
    assert config["role"] == "assistant"
    assert config["system"] == "System message\n"
    assert "description" not in config
    assert "model" not in config


@pytest.mark.asyncio
async def test_load_participant_config_caching(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    # Load config for the first time
    config1 = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    # Modify the file
    config_file = taskmates_dirs[0] / "taskmates" / f"{participant_name}.md"
    config_file.write_text("""---
role: assistant
description: Updated description
model: gpt-3.5-turbo
---
System message
""")

    # Ensure the modification time is different
    time.sleep(0.01)
    os.utime(config_file, None)

    # Load config again (should detect the change and not use cache)
    config2 = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config1 != config2
    assert config2["description"] == "Updated description"

    # Load config once more (should use cache)
    config3 = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config2 == config3
    assert config3["description"] == "Updated description"


@pytest.mark.asyncio
async def test_load_participant_config_multiple_dirs(sample_data):
    participants_configs, participant_name, taskmates_dirs = sample_data

    # Create a file in the second directory
    config_dir2 = taskmates_dirs[1] / "taskmates"
    config_dir2.mkdir(parents=True)
    (config_dir2 / f"{participant_name}.md").write_text("""---
role: assistant
model: gpt-4
---
System message
""")

    config = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config["model"] == "gpt-3.5-turbo"  # Should use the file from the first directory

    # Remove the file from the first directory
    os.remove(taskmates_dirs[0] / "taskmates" / f"{participant_name}.md")

    load_cache.clear()
    config = await load_participant_config(participants_configs, participant_name, taskmates_dirs)

    assert config["model"] == "gpt-4"  # Should now use the file from the second directory
