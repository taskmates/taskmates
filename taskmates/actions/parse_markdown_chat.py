import os
import textwrap
from pathlib import Path
from typing import Union

import pytest
from loguru import logger
from typeguard import typechecked

from taskmates.core.actions.code_execution.code_cells.parse_notebook import parse_notebook
from taskmates.formats.markdown.metadata.get_available_tools import get_available_tools
from taskmates.formats.markdown.metadata.prepend_recipient_system import prepend_recipient_system
from taskmates.formats.markdown.parsing.parse_front_matter_and_messages import parse_front_matter_and_messages
from taskmates.formats.markdown.participants.compute_participants import compute_participants
from taskmates.formats.markdown.participants.format_username_prompt import format_username_prompt
from taskmates.formats.openai.get_text_content import get_text_content
from taskmates.lib.digest_.get_digest import get_digest
from taskmates.types import Chat


@typechecked
async def parse_markdown_chat(markdown_chat: str,
                              markdown_path: Union[str, Path] | None,
                              taskmates_dirs: list[str | Path],
                              inputs: dict | None = None) -> Chat:
    logger.debug(f"Parsing markdown chat")

    if markdown_path is None:
        markdown_path = Path(os.getcwd()) / f"{get_digest(markdown_chat)}.md"
    markdown_path = Path(markdown_path)

    # parse
    split_messages, chat_front_matter = await parse_front_matter_and_messages(markdown_path,
                                                                              markdown_chat,
                                                                              "user")

    # compute
    recipient_name, recipient_front_matter, participants_configs = await compute_participants(taskmates_dirs,
                                                                                              chat_front_matter,
                                                                                              split_messages)
    available_tools = get_available_tools(chat_front_matter, recipient_front_matter)

    # post-process
    if inputs is None:
        inputs = {}
    front_matter_inputs = chat_front_matter.get("inputs", {})

    if recipient_name:
        messages = prepend_recipient_system(taskmates_dirs,
                                            participants_configs,
                                            recipient_name,
                                            recipient_front_matter,
                                            split_messages,
                                            inputs={**front_matter_inputs, **inputs})
    else:
        messages = split_messages

    recipient_config = recipient_front_matter.copy()
    # TODO: review this. We should probably isolate these properties
    recipient_config.pop("name", None)
    recipient_config.pop("description", None)
    recipient_config.pop("system", None)
    recipient_config.pop("role", None)

    completion_opts = {**recipient_config, **chat_front_matter}
    notebook, code_cells = parse_notebook(get_text_content(messages[-1]))

    if code_cells:
        messages[-1]["code_cells"] = code_cells

    return {
        'markdown_chat': markdown_chat,
        'completion_opts': completion_opts,
        'messages': messages,
        'participants': participants_configs,
        'available_tools': (list(available_tools.keys()))
    }


@pytest.fixture
def taskmates_dir(tmp_path):
    base_dir = tmp_path / ".taskmates"
    (base_dir / "engine").mkdir(parents=True)
    (base_dir / "engine" / "chat_introduction.md").write_text("CHAT_INTRODUCTION\n")
    (base_dir / "taskmates").mkdir(parents=True)
    (base_dir / "taskmates" / "mediator.md").write_text("MEDIATOR_PROMPT\n")
    (base_dir / "taskmates" / "mediator.description.md").write_text("MEDIATOR_ROLE\n")
    (base_dir / "taskmates" / "browser.md").write_text("---\ntools:\n  BROWSER_TOOL:\n---\n\nBROWSER_PROMPT\n")
    (base_dir / "taskmates" / "browser.description.md").write_text("BROWSER_ROLE\n")
    (base_dir / "taskmates" / "coder.md").write_text("CODER_PROMPT\n")
    (base_dir / "taskmates" / "coder.description.md").write_text("CODER_ROLE\n")
    return base_dir


@pytest.fixture
def markdown_path(tmp_path):
    return tmp_path / "test_chat.md"


@pytest.mark.asyncio
async def test_recipient_by_mention(taskmates_dir, markdown_path):
    markdown_chat = """\
    ---
    participants:
      browser:
        tools:
          BROWSER_TOOL:
    ---
    
    @browser search the latest news @not_a_mention
    """
    markdown_path.write_text(textwrap.dedent(markdown_chat))
    result = await parse_markdown_chat(textwrap.dedent(markdown_chat), markdown_path, [taskmates_dir])

    assert result['messages'][0]["role"] == "system"
    assert result['messages'][0]["content"] == f"BROWSER_PROMPT\n\n{format_username_prompt('browser')}\n"
    assert result['messages'][1]["content"] == "@browser search the latest news @not_a_mention\n"
    assert result['available_tools'] == ["BROWSER_TOOL"]
    assert result['messages'][-1]['recipient'] == 'browser'


@pytest.mark.asyncio
async def test_single_participant(taskmates_dir, markdown_path):
    # Example markdown chat with a participant
    markdown_chat_content = """\
    ---
    participants:
      browser:
        system: "BROWSER_PROMPT"
        tools:
            BROWSER_TOOL:
        
    ---

    Please search for the latest news on ai
    """
    markdown_path.write_text(textwrap.dedent(markdown_chat_content))

    # Process the markdown chat
    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), markdown_path, [taskmates_dir])

    # Assertions to check if the participants and system messages are processed correctly
    assert result['messages'][0]['role'] == 'system'

    # assert @browser is the recipient
    assert result['messages'][0]['content'] == f"BROWSER_PROMPT\n\n{format_username_prompt('browser')}\n"
    assert result['available_tools'] == ["BROWSER_TOOL"]

    assert result['messages'][1]['role'] == 'user'
    assert result['messages'][1]['content'] == 'Please search for the latest news on ai\n'
    assert result['messages'][-1]['recipient'] == 'browser'
    assert list(result['participants'].keys()) == ['user', 'browser']


@pytest.mark.asyncio
async def test_multiple_participants_and_recipient(taskmates_dir, markdown_path):
    # Example markdown chat with a participant
    markdown_chat_content = """\
    ---
    participants:
      browser:
        system: BROWSER_PROMPT
        description: BROWSER_ROLE
      coder:  
        system: CODER_PROMPT
        description: CODER_ROLE
    ---

    @browser Please search for the latest news on ai
    """
    markdown_path.write_text(textwrap.dedent(markdown_chat_content))

    # Process the markdown chat
    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), markdown_path, [taskmates_dir])

    # Assertions to check if the participants and system messages are processed correctly
    assert result['messages'][0]['role'] == 'system'

    expected_content = f"""\
        BROWSER_PROMPT
        
        
        CHAT_INTRODUCTION
        
        The following participants are in this chat:
        
        - @browser BROWSER_ROLE
        - @coder CODER_ROLE

        {format_username_prompt('browser')}
    """

    assert result['messages'][0]['content'] == textwrap.dedent(expected_content)

    assert result['messages'][1]['role'] == 'user'
    assert result['messages'][1]['content'] == '@browser Please search for the latest news on ai\n'
    assert result['messages'][-1]['recipient'] == 'browser'
    assert list(result['participants'].keys()) == ['user', 'browser', 'coder']


@pytest.mark.asyncio
async def test_empty_participants(markdown_path, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
    ---

    Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content),
                                       markdown_path,
                                       [taskmates_dir])

    assert list(result['participants'].keys()) == ['user', 'assistant']


@pytest.mark.asyncio
async def test_missing_user_participant(markdown_path, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
      browser:
    ---

    Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), markdown_path,
                                       [taskmates_dir])

    assert list(result['participants'].keys()) == ['user', 'browser']


@pytest.mark.asyncio
async def test_participant_dictionary_format(markdown_path, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
      my_assistant:
        system: My custom system prompt
        role: assistant
      my_other_assistant:
        role: assistant
        system: Another system prompt
    ---

    @my_assistant Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), markdown_path,
                                       [taskmates_dir])

    assert list(result['participants'].keys()) == ['user', 'my_assistant', 'my_other_assistant']
