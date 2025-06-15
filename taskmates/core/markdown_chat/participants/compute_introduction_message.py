import textwrap
from pathlib import Path

import pytest
from typeguard import typechecked

from taskmates.config.find_config_file import find_config_file


@typechecked
def compute_introduction_message(participants_dicts: dict, taskmates_dirs: list[str | Path]):
    participants_with_description = [participant for participant in participants_dicts if "description" in
                                     participants_dicts[participant]]

    if len(participants_with_description) <= 1:
        return ""

    template_file = find_config_file("engine/chat_introduction.md", taskmates_dirs)
    template = Path(template_file).read_text()

    introduction = "\n" + template + "\n"
    introduction += "The following participants are in this chat:\n\n"
    for participant in participants_with_description:
        if "description" in participants_dicts[participant]:
            introduction += f"- @{participant} " + participants_dicts[participant][
                "description"].strip() + "\n"
    return introduction


@pytest.fixture(autouse=True)
def taskmates_dir(tmp_path):
    base_config_dir = tmp_path / ".taskmates"
    engine_config_dir = base_config_dir / "engine"
    engine_config_dir.mkdir(parents=True)
    (engine_config_dir / "chat_introduction.md").write_text("THREAD_INTRODUCTION\n")
    return base_config_dir


def test_recipient_is_the_only_participant_with_description(taskmates_dir):
    recipient_is_the_only_participant_with_description = {
        "browser": {"description": "BROWSER_ROLE"}
    }
    assert compute_introduction_message(recipient_is_the_only_participant_with_description,
                                        [taskmates_dir]) == ""


def test_multiple_participants_with_description(taskmates_dir):
    participants_dicts = {
        "coder": {"description": "CODER_ROLE"},
        "browser": {"description": "BROWSER_ROLE"}
    }

    expected_introduction = """
        THREAD_INTRODUCTION
        
        The following participants are in this chat:
        
        - @coder CODER_ROLE
        - @browser BROWSER_ROLE
    """
    assert compute_introduction_message(participants_dicts,
                                        [taskmates_dir]) == textwrap.dedent(expected_introduction)
