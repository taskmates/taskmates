import textwrap

import pytest
from loguru import logger

from taskmates.core.workflows.markdown_completion.build_completion_request import build_completion_request
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.code_cell_execution_section_completion import \
    CodeCellExecutionSectionCompletion
from taskmates.core.workflows.markdown_completion.completions.section_completion import SectionCompletion
from taskmates.core.workflows.markdown_completion.completions.llm_completion.llm_chat_section_completion import \
    LlmChatSectionCompletion
from taskmates.core.workflows.markdown_completion.completions.tool_execution.tool_execution_section_completion import \
    ToolExecutionSectionCompletion
from taskmates.types import CompletionRequest


def compute_next_completion(chat: CompletionRequest) -> SectionCompletion | None:
    logger.debug("Computing next completion")

    assistances = []

    run_opts = chat.get("run_opts", {})
    is_jupyter_enabled = run_opts.get("jupyter_enabled", True)

    if is_jupyter_enabled:
        assistances.append(CodeCellExecutionSectionCompletion())

    assistances.extend([
        ToolExecutionSectionCompletion(),
        LlmChatSectionCompletion()
    ])

    for assistance in assistances:
        if assistance.can_complete(chat):
            logger.debug(f"Next completion: {assistance}")

            return assistance

    return None


@pytest.fixture
def taskmates_dir(tmp_path, transaction):
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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, CodeCellExecutionSectionCompletion)


@pytest.mark.asyncio
async def test_compute_next_completion_tool(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    Check something
    
    **assistant>** Let me check something.
    
    ###### Steps
    - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, ToolExecutionSectionCompletion)


@pytest.mark.asyncio
async def test_compute_next_completion_chat(taskmates_dir, tmp_path):
    markdown_chat = textwrap.dedent("""\
    ---
    participants: {}
    ---
    
    **user>** How much is 1 + 1?
    """)

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatSectionCompletion)


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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatSectionCompletion)


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
#     chat = await build_chat_payload(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
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
#     chat = await build_chat_payload(markdown_chat, tmp_path / "chat.md", [taskmates_dir])
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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatSectionCompletion)


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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, ToolExecutionSectionCompletion)


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

    chat = build_completion_request(markdown_chat, markdown_path=str(tmp_path / "test.md"))
    result = compute_next_completion(chat)
    assert isinstance(result, LlmChatSectionCompletion)
