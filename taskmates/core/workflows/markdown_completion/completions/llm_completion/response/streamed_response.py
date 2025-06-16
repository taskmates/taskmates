from langchain_core.messages import AIMessageChunk


class StreamedResponse:
    def __init__(self):
        self.accepted_chunks = []
        self.final_json = {}
        self.current_tool_call_id = None
        self.tool_calls_by_id = {}
        self.content_delta = ''
        self.choices = []
        self.finish_reason = None

    async def accept(self, chat_message_chunk: AIMessageChunk):
        self.accepted_chunks.append(chat_message_chunk)

        # Tool calls may be carried as additional_kwargs
        tool_calls = []
        if hasattr(chat_message_chunk, "additional_kwargs") and chat_message_chunk.additional_kwargs:
            tool_calls = chat_message_chunk.additional_kwargs.get("tool_calls", []) or []

        content = getattr(chat_message_chunk, "content", "")

        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id', None)
            arguments = tool_call['function'].get('arguments', '')

            if tool_call_id:
                self.current_tool_call_id = tool_call_id
                if self.current_tool_call_id not in self.tool_calls_by_id:
                    self.tool_calls_by_id[self.current_tool_call_id] = {
                        'id': tool_call_id,
                        'function': {
                            'name': tool_call['function'].get('name', None),
                            'arguments': ''
                        },
                        'type': 'function'
                    }

            if arguments is not None and self.current_tool_call_id:
                self.tool_calls_by_id[self.current_tool_call_id]['function']['arguments'] += arguments

        if content is not None:
            # Handle both string and list content
            if isinstance(content, str):
                self.content_delta += content
            elif isinstance(content, list):
                # Extract text from list content
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        self.content_delta += part.get("text", "")

        # Compose a dict for this chunk (for final_json aggregation), ignore 'choices'
        chunk_json = {}
        # Try to aggregate relevant fields from response_metadata, id, etc.
        if hasattr(chat_message_chunk, "response_metadata") and chat_message_chunk.response_metadata:
            chunk_json.update(chat_message_chunk.response_metadata)
        if getattr(chat_message_chunk, "id", None):
            chunk_json["id"] = chat_message_chunk.id

        # Remove "choices" if present
        if "choices" in chunk_json:
            del chunk_json['choices']
        self.final_json.update(chunk_json)

    @property
    def payload(self):
        # Compose choices block as previously
        if self.tool_calls_by_id or self.content_delta:
            message = {
                'role': 'assistant',
                'content': self.content_delta if self.content_delta else None,
            }
            if self.tool_calls_by_id:
                message['tool_calls'] = list(self.tool_calls_by_id.values())
            self.choices.append({
                'index': 0,
                'message': message,
                'finish_reason': 'tool_calls' if self.tool_calls_by_id else 'stop'
            })

        # Add the combined choices to the final_json
        self.final_json['choices'] = self.choices

        # Change the object type to "chat.completion"
        self.final_json['object'] = 'chat.completion'

        return self.final_json


# TESTS

import pytest


@pytest.mark.asyncio
async def test_streamed_response_accumulates_content_and_tool_calls():
    from langchain_core.messages import AIMessageChunk

    # Simulating a stream that includes a tool call in parts
    chunk1 = AIMessageChunk(
        content='Hello, ',
        additional_kwargs={},
        response_metadata={"model_name": "mock-model"},
        id="msg1"
    )
    chunk2 = AIMessageChunk(
        content='world.',
        additional_kwargs={'tool_calls': [
            {
                'id': 'tool1',
                'function': {'name': 'greet', 'arguments': 'arg1'},
                'type': 'function'
            }
        ]},
        response_metadata={"model_name": "mock-model"},
        id="msg2"
    )
    chunk3 = AIMessageChunk(
        content=' Done.',
        additional_kwargs={'tool_calls': [
            {
                'id': 'tool1',
                'function': {'name': 'greet', 'arguments': ' and arg2'},
                'type': 'function'
            }
        ]},
        response_metadata={"model_name": "mock-model", "finish_reason": "tool_calls"},
        id="msg3"
    )

    sr = StreamedResponse()
    await sr.accept(chunk1)
    await sr.accept(chunk2)
    await sr.accept(chunk3)

    payload = sr.payload

    # We should see concatenated content and tool_calls merged by id, with aggregated arguments
    expected_tool_calls = [{
        'id': 'tool1',
        'function': {
            'name': 'greet',
            'arguments': 'arg1 and arg2'
        },
        'type': 'function'
    }]
    expected_content = 'Hello, world. Done.'
    assert payload["choices"][0]["message"]["content"] == expected_content
    assert payload["choices"][0]["message"]["tool_calls"] == expected_tool_calls
    assert payload["choices"][0]["finish_reason"] == "tool_calls"
    assert payload["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_streamed_response_without_tool_calls_yields_stop():
    from langchain_core.messages import AIMessageChunk

    chunk1 = AIMessageChunk(
        content='Just text.',
        additional_kwargs={},
        response_metadata={"model_name": "mock-model"},
        id="m1"
    )
    chunk2 = AIMessageChunk(
        content=' Even more.',
        additional_kwargs={},
        response_metadata={"model_name": "mock-model", "finish_reason": "stop"},
        id="m2"
    )
    sr = StreamedResponse()
    await sr.accept(chunk1)
    await sr.accept(chunk2)
    payload = sr.payload

    expected_content = 'Just text. Even more.'
    assert payload["choices"][0]["message"]["content"] == expected_content
    assert "tool_calls" not in payload["choices"][0]["message"]
    assert payload["choices"][0]["finish_reason"] == "stop"
    assert payload["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_streamed_response_merges_chunk_metadata():
    from langchain_core.messages import AIMessageChunk

    chunk1 = AIMessageChunk(
        content='one',
        additional_kwargs={},
        response_metadata={"model_name": "mock-model", "foo": "bar"},
        id="id1"
    )
    chunk2 = AIMessageChunk(
        content='two',
        additional_kwargs={},
        response_metadata={"baz": "qux"},
        id="id2"
    )
    sr = StreamedResponse()
    await sr.accept(chunk1)
    await sr.accept(chunk2)
    payload = sr.payload

    assert 'foo' in payload and payload['foo'] == 'bar'
    assert 'baz' in payload and payload['baz'] == 'qux'
    assert "model_name" in payload


@pytest.mark.asyncio
async def test_streamed_response_tool_call_id_switch():
    from langchain_core.messages import AIMessageChunk

    # Multiple tool call IDs in the stream
    chunk1 = AIMessageChunk(
        content='',
        additional_kwargs={'tool_calls': [
            {
                'id': 'toolA',
                'function': {'name': 'foo', 'arguments': 'argsA1'},
                'type': 'function'
            }
        ]},
        response_metadata={},
        id="msgA"
    )
    chunk2 = AIMessageChunk(
        content='',
        additional_kwargs={'tool_calls': [
            {
                'id': 'toolB',
                'function': {'name': 'bar', 'arguments': 'argsB1'},
                'type': 'function'
            }
        ]},
        response_metadata={},
        id="msgB"
    )
    chunk3 = AIMessageChunk(
        content='',
        additional_kwargs={'tool_calls': [
            {
                'id': 'toolA',
                'function': {'name': 'foo', 'arguments': 'argsA2'},
                'type': 'function'
            }
        ]},
        response_metadata={},
        id="msgC"
    )
    sr = StreamedResponse()
    await sr.accept(chunk1)
    await sr.accept(chunk2)
    await sr.accept(chunk3)
    payload = sr.payload

    tc = sorted(payload["choices"][0]["message"]["tool_calls"], key=lambda x: x["id"])
    assert tc[0]["id"] == "toolA" and tc[0]["function"]["arguments"] == "argsA1argsA2"
    assert tc[1]["id"] == "toolB" and tc[1]["function"]["arguments"] == "argsB1"


@pytest.mark.asyncio
async def test_handles_list_content():
    """Ensures StreamedResponse can handle both string and list content without errors."""
    response = StreamedResponse()

    # Test string content
    chunk1 = AIMessageChunk(content="Hello")
    await response.accept(chunk1)
    assert response.content_delta == "Hello"

    # Test list content with text
    chunk2 = AIMessageChunk(content=[{"type": "text", "text": " world"}])
    await response.accept(chunk2)
    assert response.content_delta == "Hello world"

    # Test list content with annotations (no text)
    chunk3 = AIMessageChunk(content=[{"annotations": [{"type": "url_citation"}], "index": 0}])
    await response.accept(chunk3)
    assert response.content_delta == "Hello world"  # Should not change

    # Verify payload
    payload = response.payload
    assert payload['choices'][0]['message']['content'] == "Hello world"


@pytest.mark.asyncio
async def test_mixed_content_types_in_stream():
    """Verifies that StreamedResponse handles a stream with mixed content types."""
    response = StreamedResponse()

    # Simulate a real stream with mixed types
    chunks = [
        AIMessageChunk(content="Start"),
        AIMessageChunk(content=[{"type": "text", "text": " middle"}]),
        AIMessageChunk(content=""),  # Empty string
        AIMessageChunk(content=[{"type": "text", "text": " end"}]),
    ]

    for chunk in chunks:
        await response.accept(chunk)

    assert response.content_delta == "Start middle end"
