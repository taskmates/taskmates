import textwrap
from pathlib import Path

import pytest
from taskmates.formats.markdown.processing.filter_comments import filter_comments
from typeguard import typechecked


@typechecked
def compute_introduction_message(participants_dicts: dict, taskmates_dir: Path):
    participants_with_description = [participant for participant in participants_dicts if "description" in
                                     participants_dicts[participant]]

    if len(participants_with_description) <= 1:
        return ""

    introduction = filter_comments(
        Path(taskmates_dir / "taskmates" / "_introduction.md").read_text()) + "\n"
    introduction += f"The following participants are in this chat:\n\n"
    for participant in participants_with_description:
        if "description" in participants_dicts[participant]:
            introduction += f"- @{participant} " + participants_dicts[participant][
                "description"].strip() + f"\n"
    return introduction


@pytest.fixture(autouse=True)
def taskmates_dir(tmp_path):
    base_dir = tmp_path / "taskmates"
    (base_dir / "taskmates").mkdir(parents=True)
    (base_dir / "taskmates" / "_introduction.md").write_text("THREAD_INTRODUCTION\n")
    return base_dir


def test_recipient_is_the_only_participant_with_description(taskmates_dir):
    recipient_is_the_only_participant_with_description = {
        "browser": {"description": "BROWSER_ROLE"}
    }
    assert compute_introduction_message(recipient_is_the_only_participant_with_description, taskmates_dir) == ""


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
                                        taskmates_dir) == textwrap.dedent(expected_introduction).lstrip("\n")
