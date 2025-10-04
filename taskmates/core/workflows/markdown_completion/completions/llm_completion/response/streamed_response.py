from langchain_core.messages import AIMessageChunk


class StreamedResponse:
    def __init__(self):
        self.accepted_chunks = []
        self.final_json = {}
        self.current_tool_call_id = None
        self.tool_calls_by_id = {}
        self.tool_calls_by_index = {}  # New: track tool calls by index for streaming
        self.content_delta = ''
        self.choices = []
        self.finish_reason = None

    async def accept(self, chat_message_chunk: AIMessageChunk):
        self.accepted_chunks.append(chat_message_chunk)

        # Handle tool_call_chunks (new streaming format)
        tool_call_chunks = getattr(chat_message_chunk, "tool_call_chunks", []) or []

        # If we have tool_call_chunks, use them exclusively (don't also process additional_kwargs.tool_calls)
        has_tool_call_chunks = bool(tool_call_chunks)

        for tool_call_chunk in tool_call_chunks:
            index = tool_call_chunk.get("index", 0)

            if index not in self.tool_calls_by_index:
                # Initialize accumulator for this index
                self.tool_calls_by_index[index] = {
                    'id': None,
                    'function': {
                        'name': None,
                        'arguments': ''
                    },
                    'type': 'function'
                }

            # Update fields as they come in
            if tool_call_chunk.get("id"):
                self.tool_calls_by_index[index]['id'] = tool_call_chunk["id"]
            if tool_call_chunk.get("name"):
                self.tool_calls_by_index[index]['function']['name'] = tool_call_chunk["name"]
            if tool_call_chunk.get("args") is not None:
                # Only append non-empty args to avoid issues with initial empty strings
                args = tool_call_chunk["args"]
                if args:  # Only append if not empty string
                    self.tool_calls_by_index[index]['function']['arguments'] += args

        # Tool calls may also be carried as additional_kwargs (older format)
        # Only process these if we don't have tool_call_chunks
        tool_calls = []
        if not has_tool_call_chunks and hasattr(chat_message_chunk,
                                                "additional_kwargs") and chat_message_chunk.additional_kwargs:
            tool_calls = chat_message_chunk.additional_kwargs.get("tool_calls", []) or []

        content = getattr(chat_message_chunk, "content", "")

        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id', None)

            # Handle both OpenAI format (with 'function' key) and Gemini format (direct 'name' and 'args')
            if 'function' in tool_call:
                # OpenAI format
                function_name = tool_call['function'].get('name', None)
                arguments = tool_call['function'].get('arguments', '')
            else:
                # Gemini format
                function_name = tool_call.get('name', None)
                args = tool_call.get('args', '')
                # Convert args to string if it's a dict
                if isinstance(args, dict):
                    import json
                    arguments = json.dumps(args)
                else:
                    arguments = args

            if tool_call_id:
                self.current_tool_call_id = tool_call_id
                if self.current_tool_call_id not in self.tool_calls_by_id:
                    self.tool_calls_by_id[self.current_tool_call_id] = {
                        'id': tool_call_id,
                        'function': {
                            'name': function_name,
                            'arguments': ''
                        },
                        'type': 'function'
                    }

            if arguments and self.current_tool_call_id:  # Only append non-empty arguments
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
        # Merge tool calls from both sources
        all_tool_calls = {}

        # First add tool calls by ID (older format)
        for tool_id, tool_call in self.tool_calls_by_id.items():
            all_tool_calls[tool_id] = tool_call

        # Then add tool calls by index (newer format), using ID if available
        for index, tool_call in self.tool_calls_by_index.items():
            tool_id = tool_call.get('id')
            if tool_id:
                # If we have an ID, use it as the key (might merge with existing)
                if tool_id in all_tool_calls:
                    # Merge arguments if needed
                    existing_args = all_tool_calls[tool_id]['function']['arguments']
                    new_args = tool_call['function']['arguments']
                    if new_args and new_args not in existing_args:
                        all_tool_calls[tool_id]['function']['arguments'] += new_args
                else:
                    all_tool_calls[tool_id] = tool_call
            else:
                # No ID, use a generated key based on index
                all_tool_calls[f"index_{index}"] = tool_call

        # Compose choices block as previously
        if all_tool_calls or self.content_delta:
            message = {
                'role': 'assistant',
                'content': self.content_delta if self.content_delta else None,
            }
            if all_tool_calls:
                message['tool_calls'] = list(all_tool_calls.values())
            self.choices.append({
                'index': 0,
                'message': message,
                'finish_reason': 'tool_calls' if all_tool_calls else 'stop'
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


@pytest.mark.asyncio
async def test_handles_tool_call_chunks():
    """Test that StreamedResponse properly handles tool_call_chunks from OpenAI Format 2."""
    response = StreamedResponse()

    # Simulate the OpenAI Format 2 streaming pattern
    chunks = [
        # Initial chunk with tool name and ID
        AIMessageChunk(
            content=[],
            tool_call_chunks=[
                {"name": "get_weather", "args": "", "id": "call_123", "index": 0, "type": "tool_call_chunk"}]
        ),
        # Subsequent chunks with arguments
        AIMessageChunk(
            content=[],
            tool_call_chunks=[{"name": None, "args": '{"', "id": None, "index": 0, "type": "tool_call_chunk"}]
        ),
        AIMessageChunk(
            content=[],
            tool_call_chunks=[{"name": None, "args": 'location', "id": None, "index": 0, "type": "tool_call_chunk"}]
        ),
        AIMessageChunk(
            content=[],
            tool_call_chunks=[{"name": None, "args": '": "', "id": None, "index": 0, "type": "tool_call_chunk"}]
        ),
        AIMessageChunk(
            content=[],
            tool_call_chunks=[
                {"name": None, "args": 'San Francisco', "id": None, "index": 0, "type": "tool_call_chunk"}]
        ),
        AIMessageChunk(
            content=[],
            tool_call_chunks=[{"name": None, "args": '"}', "id": None, "index": 0, "type": "tool_call_chunk"}]
        ),
    ]

    for chunk in chunks:
        await response.accept(chunk)

    payload = response.payload

    # Verify the tool call was properly accumulated
    assert len(payload['choices']) == 1
    assert payload['choices'][0]['message']['tool_calls'] == [{
        'id': 'call_123',
        'function': {
            'name': 'get_weather',
            'arguments': '{"location": "San Francisco"}'
        },
        'type': 'function'
    }]
    assert payload['choices'][0]['finish_reason'] == 'tool_calls'
