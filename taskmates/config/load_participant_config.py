import os
from pathlib import Path
from typing import Union

import pytest
import time
from typeguard import typechecked

from taskmates.formats.markdown.parsing.parse_front_matter_and_messages import parse_front_matter_and_messages
from taskmates.formats.markdown.processing.filter_comments import filter_comments

load_cache = {}


@typechecked
async def load_participant_config(participants_configs: dict,
                                  participant_name: str,
                                  taskmates_dir: Union[str, Path]) -> dict:
    def get_file_mtime(file_path):
        return os.path.getmtime(file_path) if file_path and os.path.exists(file_path) else None

    def find_config(name):
        matching_files = sorted(Path(taskmates_dir).glob(f"*/{name}"))
        return matching_files[0] if matching_files else None

    participant_md_path = find_config(f"{participant_name}.md")
    participant_description_md_path = find_config(f"{participant_name}.description.md")
    participant_model_md_path = find_config(f"{participant_name}.model.md")

    current_mtimes = {
        "md": get_file_mtime(participant_md_path),
        "description": get_file_mtime(participant_description_md_path),
        "model": get_file_mtime(participant_model_md_path)
    }

    if participant_name in load_cache:
        cached_config, cached_mtimes = load_cache[participant_name]
        if all(current_mtimes[key] == cached_mtimes[key] for key in current_mtimes):
            return cached_config

    updated_participant_config = (participants_configs.get(participant_name) or {}).copy()
    updated_participant_config["name"] = participant_name

    # process system
    if participant_md_path and participant_md_path.exists():
        content = participant_md_path.read_text()
        messages, front_matter = await parse_front_matter_and_messages(participant_md_path, content,
                                                                       "system")
        if len(messages) != 1:
            raise ValueError("Multi-messages taskmate definitions not supported yet")

        updated_participant_config["system"] = messages[0]["content"]
        updated_participant_config.update(front_matter)
    elif "system" in updated_participant_config:
        del updated_participant_config["system"]

    # process description
    if participant_description_md_path and participant_description_md_path.exists():
        updated_participant_config["description"] = filter_comments(participant_description_md_path.read_text())
    elif "description" in updated_participant_config:
        del updated_participant_config["description"]

    # process model
    if participant_model_md_path and participant_model_md_path.exists():
        updated_participant_config["model"] = filter_comments(participant_model_md_path.read_text()).strip()
    elif "model" in updated_participant_config:
        del updated_participant_config["model"]

    # compute default role
    if "role" not in updated_participant_config:
        if (participant_name == "assistant" or
                "system" in updated_participant_config or
                "tools" in updated_participant_config):
            updated_participant_config["role"] = "assistant"
        else:
            updated_participant_config["role"] = "user"

    load_cache[participant_name] = (updated_participant_config, current_mtimes)
    return updated_participant_config


@pytest.fixture
def sample_data(tmp_path):
    participants_configs = {
        "assistant1": {"role": "assistant", "system": "existing system info"}
    }
    participant_name = "assistant1"
    taskmates_dir = tmp_path / "opt" / "taskmates"
    taskmates_dir.mkdir(parents=True)

    return participants_configs, participant_name, taskmates_dir


@pytest.mark.asyncio
async def test_default_role_assignment_with_md(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    md_path = taskmates_dir / "taskmates" / f"{participant_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("You're a helpful assistant")

    config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config["role"] == "assistant", "Should set role to assistant when markdown file exists"


@pytest.mark.asyncio
async def test_process_system_with_single_message(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    md_path = taskmates_dir / "taskmates" / f"{participant_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("---\nextra: data\n---\n\nHello")
    config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config["system"] == "Hello", "Should process system message correctly"
    assert config["extra"] == "data", "Should update config with front matter"


@pytest.mark.asyncio
async def test_error_on_multiple_messages(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    md_path = taskmates_dir / "taskmates" / f"{participant_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("**john>**\n\nHello\n\nWorld\n\n**doe>**\n\nGoodbye\n\n")
    with pytest.raises(ValueError, match="Multi-messages taskmate definitions not supported yet"):
        await load_participant_config(participants_configs, participant_name, taskmates_dir)


@pytest.mark.asyncio
async def test_default_role_assignment_no_md(sample_data):
    participants_configs, participant_name, taskmates_dir = sample_data
    config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config["role"] == "assistant", "Should use the role specified in the configuration"


@pytest.mark.asyncio
async def test_process_description(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    description_path = taskmates_dir / "taskmates" / f"{participant_name}.description.md"
    description_path.parent.mkdir(parents=True, exist_ok=True)
    description_path.write_text("# Heading\nFiltered description")
    config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config["description"] == "# Heading\nFiltered description", "Should process description correctly"


@pytest.mark.asyncio
async def test_process_model(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    model_path = taskmates_dir / "taskmates" / f"{participant_name}.model.md"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text("gpt-3.5-turbo\n")
    config = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config["model"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_multiple_matching_directories(sample_data, tmp_path):
    participants_configs, _participant_name, taskmates_dir = sample_data
    team_dir1 = taskmates_dir / "team1"
    team_dir1.mkdir(parents=True)
    md_path1 = team_dir1 / f"assistant1.md"
    md_path1.write_text("Hello from taskmates1")

    team_dir2 = taskmates_dir / "team2"
    team_dir2.mkdir(parents=True)
    md_path2 = team_dir2 / f"assistant1.md"
    md_path2.write_text("Hello from taskmates2")

    config = await load_participant_config(participants_configs, "assistant1", taskmates_dir)
    assert config["system"] == "Hello from taskmates1", "Should pick the first matching directory"


@pytest.mark.asyncio
async def test_cache_reload_on_file_change(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    md_path = taskmates_dir / "taskmates" / f"{participant_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("Initial content")

    # First load
    config1 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config1["system"] == "Initial content"

    # Wait a bit to ensure file modification time changes
    time.sleep(0.1)

    # Modify the file
    md_path.write_text("Updated content")

    # Second load should reflect the changes
    config2 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config2["system"] == "Updated content"


@pytest.mark.asyncio
async def test_cache_reload_on_file_deletion(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    md_path = taskmates_dir / "taskmates" / f"{participant_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("Initial content")

    # First load
    config1 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config1["system"] == "Initial content"

    # Delete the file
    md_path.unlink()

    # Second load should not have the 'system' key
    config2 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert "system" not in config2


@pytest.mark.asyncio
async def test_cache_reload_on_description_change(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    description_path = taskmates_dir / "taskmates" / f"{participant_name}.description.md"
    description_path.parent.mkdir(parents=True, exist_ok=True)
    description_path.write_text("Initial description")

    # First load
    config1 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config1["description"] == "Initial description"

    # Wait a bit to ensure file modification time changes
    time.sleep(0.1)

    # Modify the file
    description_path.write_text("Updated description")

    # Second load should reflect the changes
    config2 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config2["description"] == "Updated description"


@pytest.mark.asyncio
async def test_cache_reload_on_model_change(sample_data, tmp_path):
    participants_configs, participant_name, taskmates_dir = sample_data
    model_path = taskmates_dir / "taskmates" / f"{participant_name}.model.md"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text("gpt-3.5-turbo")

    # First load
    config1 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config1["model"] == "gpt-3.5-turbo"

    # Wait a bit to ensure file modification time changes
    time.sleep(0.1)

    # Modify the file
    model_path.write_text("gpt-4")

    # Second load should reflect the changes
    config2 = await load_participant_config(participants_configs, participant_name, taskmates_dir)
    assert config2["model"] == "gpt-4"
