import json
import platform
import textwrap

import pytest
from quart import Quart
from quart.testing.connections import WebsocketDisconnectError
from typeguard import typechecked

import taskmates
from taskmates.config.server_config import SERVER_CONFIG
from taskmates.server.blueprints.taskmates_completions import completions_bp as completions_v2_bp
from taskmates.types import CompletionPayload


@pytest.fixture
def app():
    app = Quart(__name__)
    app.register_blueprint(completions_v2_bp, name='completions_v2')
    return app


@pytest.fixture(autouse=True)
def server_config(tmp_path):
    token = SERVER_CONFIG.set({"taskmates_dir": str(tmp_path / "taskmates")})
    try:
        SERVER_CONFIG.set(SERVER_CONFIG.get())
        yield
    finally:
        SERVER_CONFIG.reset(token)


@pytest.mark.timeout(5)
async def test_chat_completion(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    Short answer. 1+1=
    
    """)

    expected_response = textwrap.dedent("""\
    **assistant>** 
    > Short answer. 1+1=
    > 
    > 
    
    **user>** """)

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_request_id",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_chat_completion_with_mention(app, tmp_path):
    test_client = app.test_client()

    (tmp_path / "taskmates" / "taskmates").mkdir(parents=True)
    (tmp_path / "taskmates" / "taskmates" / "jeff.md").write_text("You're a helpful assistant\n")

    markdown_chat = textwrap.dedent("""\
    Hey @jeff short answer. 1+1=
    
    """)

    expected_response = textwrap.dedent("""\
    **jeff>** 
    > Hey @jeff short answer. 1+1=
    > 
    > 
    
    **user>** """)

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_request_id",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        }
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_tool_completion(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    How much is 1 + 1?
    
    **assistant>**
    
    How much is 1 + 1?
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd":"python -c \\"print(1 + 1)\\""}`
    
    """)

    expected_response = ('###### Execution: Run Shell Command [1]\n'
                         '\n'
                         "<pre class='output' style='display:none'>\n"
                         '2\n'
                         '\n'
                         'Exit Code: 0\n'
                         '</pre>\n'
                         '-[x] Done\n'
                         '\n'
                         "**assistant>** ")

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_echo_tool",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_code_cell_completion(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    print(1 + 1)
    
    **assistant>**
    
    print(1 + 1)
    
    ```python .eval
    print(1 + 1)
    ```
    
    """)

    expected_completion = textwrap.dedent('''\
    ###### Cell Output: stdout [cell_0]

    <pre>
    2
    </pre>

    **assistant>** ''')

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_echo_code_cell",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_completion


@pytest.mark.timeout(5)
async def test_error_completion(app, tmp_path):
    test_client = app.test_client()

    expected_completion_prefix = "**error>** "

    expected_completion_suffix = textwrap.dedent("""\
        </pre>
    """)

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": "REQUEST\n\n",
        "completion_context": {
            "request_id": "test_error_completion",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "non-existent-model",
        },
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response.startswith(expected_completion_prefix)
    assert markdown_response.endswith(expected_completion_suffix)


@pytest.mark.timeout(5)
async def test_interrupt_tool(app, tmp_path):
    test_client = app.test_client()

    if platform.system() == "Windows":
        cmd = "for /L %i in (1,1,10) do @(echo %i & timeout /t 1 > nul)"
    else:
        cmd = "seq 5; sleep 1; seq 6 10"

    markdown_chat = textwrap.dedent(f"""\
    Run a command that prints numbers from 1 to 10 with a 1-second delay between each number.
    
    **assistant>**
    
    Certainly! I'll run a command that prints numbers from 1 to 10 with a 1-second delay between each number.
    
    ###### Steps
    
    - Run Shell Command [1] `{{"cmd":"{cmd}"}}`
    
    """)

    if platform.system() == "Windows":
        expected_response = ('###### Execution: Run Shell Command [1]\n'
                             '\n'
                             "<pre class='output' style='display:none'>\n"
                             '1\n'
                             '2\n'
                             '3\n'
                             '--- INTERRUPT ---\n'
                             '\n'
                             'Exit Code: 1\n'
                             '</pre>\n'
                             '-[x] Done\n'
                             '\n')
    else:
        expected_response = ('###### Execution: Run Shell Command [1]\n'
                             '\n'
                             "<pre class='output' style='display:none'>\n"
                             '1\n'
                             '2\n'
                             '3\n'
                             '4\n'
                             '5\n'
                             '--- INTERRUPT ---\n'
                             '\n'
                             'Exit Code: -2\n'
                             '</pre>\n'
                             '-[x] Done\n'
                             '\n')

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_interrupt_tool",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    async with test_client.websocket('/v2/taskmates/completions') as ws:
        await ws.send(json.dumps(test_payload))
        messages = []

        while True:
            message = json.loads(await ws.receive())
            messages.append(message)
            if message["type"] == "completion":
                if "5" in message["payload"]["markdown_chunk"]:
                    break

        await ws.send(json.dumps({"type": "interrupt", "completion_context": {"request_id": "test_interrupt_tool"}}))

        remaining = await collect_until_closed(ws)
        messages.extend(remaining)

    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_code_cell_no_output(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    print(1 + 1)
    
    **assistant>**
    
    print(1 + 1)
    
    ```python .eval
    # This code cell doesn't produce any output
    ```
    
    """)

    expected_completion = ('###### Cell Output: stdout [cell_0]\n'
                           '\n'
                           'Done\n'
                           '\n'
                           '**assistant>** ')
    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_echo_code_cell_no_output",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    messages = await send_and_collect_messages(test_client, test_payload, '/v2/taskmates/completions')
    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_completion


@pytest.mark.timeout(5)
async def test_interrupt_code_cell(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    How much is 1 + 1?
    
    **assistant>**
    
    How much is 1 + 1?
    
    ```python .eval
    import time
    print(2)
    time.sleep(60)
    print('fail')
    ```
    
    """)

    expected_response = ('###### Cell Output: stdout [cell_0]\n'
                         '\n'
                         '<pre>\n'
                         '2\n'
                         '</pre>\n'
                         '\n'
                         '###### Cell Output: error [cell_0]\n'
                         '\n'
                         '<pre>\n'
                         '---------------------------------------------------------------------------\n'
                         'KeyboardInterrupt                         Traceback (most recent call last)\n'
                         'Cell In[4], line 3\n'
                         '      1 import time\n'
                         '      2 print(2)\n'
                         '----&gt; 3 time.sleep(60)\n'
                         "      4 print('fail')\n"
                         '\n'
                         'KeyboardInterrupt: \n'
                         '</pre>\n'
                         '\n')

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_echo_tool",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    async with test_client.websocket('/v2/taskmates/completions') as ws:
        await ws.send(json.dumps(test_payload))
        messages = []

        while True:
            message = json.loads(await ws.receive())
            messages.append(message)
            if message["type"] == "completion":
                if "2" in message["payload"]["markdown_chunk"]:
                    break

        await ws.send(json.dumps({"type": "interrupt", "completion_context": {"request_id": "test_echo_tool"}}))

        remaining = await collect_until_closed(ws)
        messages.extend(remaining)

    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_kill_tool(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    Run a command that ignores SIGINT
    
    **assistant>**
    
    Certainly! I'll run a command that ignores the SIGINT signal.
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd":"trap '' INT; echo Starting; sleep 60; echo fail"}`
    
    """)

    expected_response = ('###### Execution: Run Shell Command [1]\n'
                         '\n'
                         "<pre class='output' style='display:none'>\n"
                         'Starting\n'
                         '--- KILL ---\n\n'
                         'Exit Code: -9\n'
                         '</pre>\n'
                         '-[x] Done\n'
                         '\n')

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_kill_tool",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    async with test_client.websocket('/v2/taskmates/completions') as ws:
        await ws.send(json.dumps(test_payload))
        messages = []

        while True:
            message = json.loads(await ws.receive())
            messages.append(message)
            if message["type"] == "completion":
                if "Starting" in message["payload"]["markdown_chunk"]:
                    break

        await ws.send(json.dumps({"type": "kill", "completion_context": {"request_id": "test_kill_tool"}}))

        remaining = await collect_until_closed(ws)
        messages.extend(remaining)

    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


@pytest.mark.timeout(5)
async def test_kill_code_cell(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    Run a command that ignores SIGINT in a code cell
    
    **assistant>**
    
    Certainly! I'll run a command that ignores the SIGINT signal in a code cell.
    
    ```python .eval
    !trap '' INT; echo Starting; sleep 60; echo fail
    ```
    
    """)

    expected_response = '###### Cell Output: stdout [cell_0]\n\n<pre>\nStarting\r\n</pre>\n\n'

    test_payload: CompletionPayload = {
        "type": "completions_request",
        "version": taskmates.__version__,
        "markdown_chat": markdown_chat,
        "completion_context": {
            "request_id": "test_kill_code_cell",
            "cwd": str(tmp_path),
            "markdown_path": str(tmp_path / "test.md"),
        },
        "completion_opts": {
            "model": "quote",
        },
    }

    async with test_client.websocket('/v2/taskmates/completions') as ws:
        await ws.send(json.dumps(test_payload))
        messages = []

        while True:
            message = json.loads(await ws.receive())
            messages.append(message)
            if message["type"] == "completion":
                if "Starting" in message["payload"]["markdown_chunk"]:
                    break

        await ws.send(json.dumps({"type": "kill", "completion_context": {"request_id": "test_kill_code_cell"}}))

        remaining = await collect_until_closed(ws)
        messages.extend(remaining)

    markdown_response = await get_markdown_response(messages)

    assert markdown_response == expected_response


async def get_markdown_response(messages):
    markdown_response = ""
    for message in messages:
        payload = message["payload"]
        if "markdown_chunk" in payload:
            markdown_response += payload["markdown_chunk"]
    return markdown_response


@typechecked
async def send_and_collect_messages(client, payload: CompletionPayload, endpoint: str):
    async with client.websocket(endpoint) as ws:
        await ws.send(json.dumps(payload))
        return await collect_until_closed(ws)


async def collect_until_closed(ws):
    messages = []
    try:
        while True:
            received = await ws.receive()
            message = json.loads(received)
            messages.append(message)
    except WebsocketDisconnectError:
        pass
    return messages
