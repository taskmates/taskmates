import textwrap

import pytest
from loguru import logger

from taskmates.core.markdown_chat.parse_markdown_chat import parse_markdown_chat
from taskmates.core.workflows.markdown_completion.completions.llm_completion.llm_chat_completion_provider import LlmChatCompletionProvider
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.workflows.markdown_completion.completions.tool_execution.tool_execution_completion_provider import \
    ToolExecutionCompletionProvider


def compute_next_completion(chat):
    logger.debug("Computing next completion")

    assistances = [
        CodeCellExecutionCompletionProvider(),
        ToolExecutionCompletionProvider(),
        LlmChatCompletionProvider()
    ]

    for assistance in assistances:
        if assistance.can_complete(chat):
            logger.debug(f"Next completion: {assistance}")

            return assistance

    return None


@pytest.fixture
def taskmates_dir(tmp_path):
    base_dir = tmp_path / ".taskmates"
    (base_dir / "engine").mkdir(parents=True)
    (base_dir / "engine" / "chat_introduction.md").write_text("CHAT_INTRODUCTION\n")
    (base_dir / "taskmates").mkdir(parents=True)
    (base_dir / "taskmates" / "assistant.md").write_text("ASSISTANT_PROMPT\n")
    (base_dir / "taskmates" / "assistant.description.md").write_text("ASSISTANT_ROLE\n")
    return base_dir


@pytest.mark.asyncio
async def test_compute_next_completion_code_cell(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** Let's calculate something
    
    **assistant>** I'll help you calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, CodeCellExecutionCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_tool(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    **assistant>** Let me check something.
    
    ###### Steps
    - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, ToolExecutionCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_chat(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** How much is 1 + 1?
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_incomplete_code_cell(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** Let's calculate
    
    **assistant>** Here's the calculation:
    
    ```python .eval
    print(1 + 1)
    
    """)  # Note: missing closing ```

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatCompletionProvider)


# TODO: not supported yet
# @pytest.mark.asyncio
# async def test_compute_next_completion_incomplete_tool_call(taskmates_dir, tmp_path):
#     markdown_chat = textwrap.dedent("""\
#     ---
#     participants:
#       assistant:
#         tools:
#           run_shell_command:
#     ---
#
#     **assistant>** Let me check something.
#
#     ###### Steps
#     - Run Shell Command [1] `{"cmd":"cd
#     """).rstrip()  # Note: missing closing tags and output
#
#     chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
#     result = compute_next_completion(chat)
#     assert isinstance(result, ChatCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_completed_chat(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** How much is 1 + 1?
    
    **assistant>** 1 + 1 equals 2
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert result is None


# TODO:
# @pytest.mark.asyncio
# async def test_compute_next_completion_empty_chat(taskmates_dir, tmp_path):
#     markdown_chat = textwrap.dedent("""\
#     ---
#     participants: {}
#     ---
#     """)
#
#     chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
#     result = compute_next_completion(chat)
#     assert result is None


@pytest.mark.asyncio
async def test_compute_next_completion_code_cell_with_error(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** Let's try something that will fail
    
    **assistant>** Here's a calculation that will fail:
    
    ```python .eval
    print(1/0)
    ```
    
    ###### Cell Output: error [cell_0]
    
    <pre>
    ZeroDivisionError: division by zero
    </pre>
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_mixed_incomplete_states(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    **user>** Let's do some calculations and check the system
    
    **assistant>** First, let's calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    
    ###### Cell Output: stdout [cell_0]
    
    <pre>
    2
    </pre>
    
    Now let me check the directory.
    
    ###### Steps
    - Run Shell Command [1] `{"cmd":"ls"}`
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, ToolExecutionCompletionProvider)


@pytest.mark.asyncio
async def test_compute_next_completion_malformed_chat(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** Hello
    
    This is a malformed message without proper formatting
    
    **user>** What should I do?
    """)

    chat = await parse_markdown_chat(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatCompletionProvider)
