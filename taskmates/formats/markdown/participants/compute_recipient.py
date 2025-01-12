import textwrap

import pytest
from loguru import logger
from typeguard import typechecked

from taskmates.formats.markdown.participants.parse_mention import parse_mention
from taskmates.formats.openai.get_text_content import get_text_content


@typechecked
def compute_recipient(messages, participants_configs) -> str | None:
    recipient = None

    participants = list(participants_configs.keys())
    participant_messages = [message for message in messages
                            if message["role"] not in ("system", "tool")
                            and message.get("name") not in ("cell_output",)
                            ]

    if not participant_messages:
        return None

    last_participant_message = participant_messages[-1]
    last_participant_message.setdefault("name", last_participant_message.get("role"))
    last_participant_message_role = participants_configs.get(last_participant_message["name"], {}).get("role")

    mention = None
    if last_participant_message is not None:
        # parse @mentions
        mention = parse_mention(get_text_content(last_participant_message), participants)

    is_self_mention = mention == messages[-1].get("name")
    is_tool_reply = messages[-1]["role"] == "tool"
    is_code_cell_reply = messages[-1].get("name") == "cell_output"

    if mention and not is_self_mention and not is_tool_reply:
        recipient = mention

    # code cell/tool call: resume conversation with caller
    elif is_tool_reply or is_code_cell_reply:
        recipient = last_participant_message["name"]

    # code cell/tool caller: resume conversation with requester
    elif len(messages) > 2 and (messages[-2]["role"] == "tool" or messages[-2].get("name") == "cell_output"):
        output_message = messages[-2]

        requesting_message = None
        for msg in reversed(messages[:-2]):  # exclude current message
            if msg["role"] not in ("tool",) and msg.get("name") not in ("cell_output",):
                requesting_message = msg
                break

        if not requesting_message:
            raise ValueError()

        if messages[-1]["name"] != output_message["recipient"]:
            recipient = output_message["recipient"]
        else:
            recipient = requesting_message["recipient"]

    # alternating participants
    elif len(participants) == 2 and "user" in participants:
        recipient = [participant for participant in participants
                     if participant != last_participant_message.get("name", last_participant_message.get("role"))][0]

    # default: assistant reply to request
    elif last_participant_message_role == "assistant" and len(participant_messages) > 1:
        recipient = participant_messages[-2]["name"]

    # re-initiate conversation
    elif last_participant_message_role == "user":
        # search last assistant message
        for message in reversed(participant_messages):
            if message["name"] != last_participant_message["name"]:
                recipient = message["name"]
                break

    logger.debug(f"Computed recipient: {recipient}")
    return recipient


# Test cases

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


@pytest.mark.asyncio
async def test_implicit_assistant(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants: {}
    ---

    **user>** Hello
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "assistant"


@pytest.mark.asyncio
async def test_mention_reply(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      alice:
        system: true
    ---

    **user>** Hello

    **dave>** Hey @alice how much is 1 + 1?

    **alice>** 2
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "dave"


@pytest.mark.asyncio
async def test_mention(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      assistant1:
        system: true
      assistant2: {}
    ---

    **user>** Hello @assistant2
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "assistant2"


@pytest.mark.asyncio
async def test_alternating(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      assistant1:
        system: true
    ---

    **user>** Hello

    **assistant1>** Hi there

    **user>** How are you?
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "assistant1"


@pytest.mark.asyncio
async def test_tool_call(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    **user>** Check the current directory
    
    **assistant>** I'll help you check the current directory using the `pwd` (print working directory) command.
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd": "pwd"}`
    
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "user"


@pytest.mark.asyncio
async def test_tool_call_response(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    **user>** Check the current directory
    
    **assistant>** I'll help you check the current directory using the `pwd` (print working directory) command.
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd": "pwd"}`
    
    ###### Execution: Run Shell Command [1]
    
    <pre class='output' style='display:none'>
    /tmp
    
    Exit Code: 0
    </pre>
    -[x] Done
    
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "assistant"  # The tool output should be handled by the assistant that called it


@pytest.mark.asyncio
async def test_tool_call_and_assistant_reply(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      assistant:
        tools:
          run_shell_command:
    ---
    
    **user>** Check the current directory
    
    **assistant>** I'll help you check the current directory using the `pwd` (print working directory) command.
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd": "pwd"}`
    
    ###### Execution: Run Shell Command [1]
    
    <pre class='output' style='display:none'>
    /tmp
    
    Exit Code: 0
    </pre>
    -[x] Done
    
    **assistant>** 
    
    The current directory is `/tmp`.
    
    
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "user"  # The tool output should be handled by the assistant that called it


@pytest.mark.asyncio
async def test_code_cell(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      coder:
        system: true
    ---
    
    **user>** Calculate something
    
    **coder>** I'll help you calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "user"


@pytest.mark.asyncio
async def test_code_cell_execution(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      coder:
        system: true
    ---
    
    **user>** Calculate something
    
    **coder>** I'll help you calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    ###### Cell Output: stdout [cell_0]
    
    Done
    
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "coder"


@pytest.mark.asyncio
async def test_code_cell_execution_and_assistant_reply(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      coder:
        system: true
    ---
    
    **user>** Calculate something
    
    **coder>** I'll help you calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    ###### Cell Output: stdout [cell_0]
    
    Done
    
    **coder>** 1+1=2
    
    
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "user"  # The code cell output should be handled by the assistant that executed it


@pytest.mark.asyncio
async def test_code_cell_execution_and_user_interruption(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      coder:
        system: true
    ---
    
    **user>** Calculate something
    
    **coder>** I'll help you calculate:
    
    ```python .eval
    print(1 + 1)
    ```
    ###### Cell Output: stdout [cell_0]
    
    Done
    
    **user>** Good, calculate something more
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "coder"  # The code cell output should be handled by the assistant that executed it


@pytest.mark.asyncio
async def test_code_cell_error_handling(taskmates_dir, tmp_path):
    from taskmates.actions.parse_markdown_chat import parse_markdown_chat

    markdown_chat = """\
    ---
    participants:
      coder:
        system: true
    ---
    
    **user>** @coder Let's try something that will fail
    
    **coder>** Here's a calculation that will fail:
    
    ```python .eval
    print(1/0)
    ```
    
    ###### Cell Output: error [cell_0]
    
    <pre>
    ---------------------------------------------------------------------------
    ZeroDivisionError                         Traceback (most recent call last)
    Cell In[4], line 1
    ----&gt; 1 print(1/0)
    
    ZeroDivisionError: division by zero
    </pre>
    
    **coder>** Done
    """

    chat = await parse_markdown_chat(textwrap.dedent(markdown_chat), tmp_path / "chat.md", [taskmates_dir])
    recipient = compute_recipient(chat['messages'], chat['participants'])
    assert recipient == "user"
