import textwrap

import pytest

from taskmates.actions.parse_markdown_chat import parse_markdown_chat


@pytest.fixture
def transclusions_base_dir(tmp_path):
    return tmp_path / "transclusions"


@pytest.fixture
def taskmates_dir(tmp_path):
    return tmp_path / "assistants"


@pytest.mark.asyncio
async def test_empty_participants(transclusions_base_dir, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
    ---

    Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content),
                                       str(transclusions_base_dir),
                                       taskmates_dir)

    assert result['participants'] == ['user', 'assistant']


@pytest.mark.asyncio
async def test_missing_user_participant(transclusions_base_dir, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
      browser:
    ---

    Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), str(transclusions_base_dir),
                                       taskmates_dir)

    assert result['participants'] == ['user', 'browser']


@pytest.mark.asyncio
async def test_participant_dictionary_format(transclusions_base_dir, taskmates_dir):
    markdown_chat_content = """\
    ---
    participants:
      my_assistant:
        type: assistant
        system: My custom system prompt
        role: My custom role description
      my_user:
        type: user
    ---

    @my_assistant Please search for the latest news on ai
    """

    result = await parse_markdown_chat(textwrap.dedent(markdown_chat_content), str(transclusions_base_dir),
                                       taskmates_dir)

    assert result['participants'] == ['user', 'my_assistant', 'my_user']
