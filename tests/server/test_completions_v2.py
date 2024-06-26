import json
import textwrap

import pytest
from quart import Quart
from quart.testing.connections import WebsocketDisconnectError
from typeguard import typechecked

from taskmates.config import SERVER_CONFIG
from taskmates.server.blueprints.taskmates_completions import completions_bp as completions_v2_bp
from taskmates.types import CompletionPayload


@pytest.fixture
def app():
    app = Quart(__name__)
    app.register_blueprint(completions_v2_bp, name='completions_v2')
    return app


@pytest.fixture(autouse=True)
def server_config(tmp_path):
    SERVER_CONFIG.set({"taskmates_dir": str(tmp_path / "taskmates")})


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_chat_completion_with_mention(app, tmp_path):
    test_client = app.test_client()

    (tmp_path / "taskmates" / "taskmates").mkdir(parents=True)
    (tmp_path / "taskmates" / "taskmates" / "alice.md").write_text("You're a helpful assistant\n")

    markdown_chat = textwrap.dedent("""\
    Hey @alice short answer. 1+1=
    
    """)

    expected_response = textwrap.dedent("""\
    **alice>** 
    > Hey @alice short answer. 1+1=
    > 
    > 
    
    **user>** """)

    test_payload: CompletionPayload = {
        "type": "completions_request",
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


@pytest.mark.asyncio
async def test_tool_completion(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    How much is 1 + 1?
    
    **assistant>**
    
    How much is 1 + 1?
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd":"echo $((1 + 1))"}`
    
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_error_completion(app, tmp_path):
    test_client = app.test_client()

    expected_completion_prefix = "**error>** "

    expected_completion_suffix = textwrap.dedent("""\
        </pre>
    """)

    test_payload: CompletionPayload = {
        "type": "completions_request",
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


@pytest.mark.asyncio
async def test_interrupt_tool(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    How much is 1 + 1?
    
    **assistant>**
    
    How much is 1 + 1?
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd":"echo 2; sleep 60; echo fail"}`
    
    """)

    expected_response = ('###### Execution: Run Shell Command [1]\n'
                         '\n'
                         "<pre class='output' style='display:none'>\n"
                         '2\n'
                         '--- INTERRUPTED ---\n'
                         'Exit Code: -2\n'
                         '</pre>\n'
                         '-[x] Done\n'
                         '\n')

    test_payload: CompletionPayload = {
        "type": "completions_request",
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_interrupt_code_cell(app, tmp_path):
    test_client = app.test_client()

    markdown_chat = textwrap.dedent("""\
    How much is 1 + 1?
    
    **assistant>**
    
    How much is 1 + 1?
    
    ```python .eval
    !echo 2; sleep 60; echo fail
    ```
    
    """)

    expected_response = '###### Cell Output: stdout [cell_0]\n\n<pre>\n2\r\n^C\r\n</pre>\n\n'
    test_payload: CompletionPayload = {
        "type": "completions_request",
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
            message = json.loads(await ws.receive())
            messages.append(message)
    except WebsocketDisconnectError:
        pass
    return messages
