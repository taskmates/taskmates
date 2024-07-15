import asyncio
import json
from typing import Dict, List, Optional, Any

import anthropic
import pytest
from anthropic import APIStatusError
from anthropic.types import MessageStartEvent, ContentBlockDeltaEvent, MessageStopEvent, TextBlock, \
    ContentBlockStartEvent, ContentBlockStopEvent, MessageDeltaEvent, TextDelta
from anthropic.types.beta.tools import ToolsBetaMessage, ToolUseBlock, ToolsBetaContentBlockStartEvent, \
    ToolsBetaContentBlockDeltaEvent, InputJsonDelta
from typeguard import typechecked

from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.request.convert_and_merge_messages import \
    convert_and_merge_messages
from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.response.convert_anthropic_tool_call_to_openai import \
    convert_anthropic_tool_call_to_openai
from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.request.convert_openai_tools_to_anthropic import \
    convert_openai_tools_to_anthropic
from taskmates.assistances.chat_completion.openai_adapters.anthropic_openai_adapter.parsing.split_system_message import \
    split_system_message
from taskmates.function_registry import function_registry
from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel
from taskmates.lib.openai_.model.delta_model import DeltaModel
from taskmates.lib.tool_schemas_.tool_schema import tool_schema
from taskmates.logging import file_logger
from taskmates.signals import SIGNALS


class AsyncAnthropicOpenAIAdapter:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic()

    @typechecked
    async def create(self,
                     model: str,
                     stream: bool,
                     messages: List[Dict[str, Any]],
                     max_tokens=1024,
                     seed=None,  # ignored
                     tools: Optional[List[Dict]] = None,
                     tool_choice: Optional[str] = None,
                     stop: Optional[List[str]] = None,
                     **kwargs
                     ):

        async def inner():
            processed_messages = convert_and_merge_messages(messages)
            chat_messages, system_message = split_system_message(processed_messages)

            # TODO: It's unfortunate that anthropic enforces tools to be re-declared for each usage.
            # Hopefully they will change it and this can be removed one day.
            #
            # Meanwhile, we should think of a workaround that doesn't expose tools to unrelated taskmates.
            # Maybe the alternative would be to not send raw text in these cases.
            anthropic_tools = convert_openai_tools_to_anthropic(tools) if tools else []
            for message in processed_messages:
                if isinstance(message["content"], str):
                    continue
                for content in message["content"]:
                    if content["type"] == "tool_use":
                        function_name = content["name"]
                        if function_name in [t["name"] for t in anthropic_tools]:
                            continue
                        function = function_registry[function_name]
                        function_schema = tool_schema(function)
                        anthropic_tools.extend(convert_openai_tools_to_anthropic([function_schema]))

            anthropic_tools = anthropic_tools or None

            stop_sequences = stop if stop else None

            payload = dict(
                max_tokens=max_tokens,
                system=system_message['content'] if system_message else None,
                messages=chat_messages,
                model=model,
                stream=stream,
                tools=anthropic_tools,
                stop_sequences=stop_sequences,
                **kwargs
            )

            if payload['tools']:
                resource = self.client.beta.tools.messages
            else:
                resource = self.client.messages

            if payload['tools'] is None:
                del payload['tools']

            if payload['stop_sequences'] is None:
                del payload['stop_sequences']

            if payload['system'] is None:
                del payload['system']

            retry_delays = [0.01, 0.1, 0.2, 0.4]  # Delays in seconds
            max_attempts = len(retry_delays) + 1

            for attempt in range(1, max_attempts + 1):
                try:
                    # TODO: Add tracing
                    signals = SIGNALS.get()
                    await signals.artifacts.send_async({"name": "anthropic_request_payload.json", "content": payload})
                    chat_completion = await resource.create(**payload)
                    id, created, model_name = None, None, model
                    is_tool_call = False

                    if isinstance(chat_completion, ToolsBetaMessage):
                        id = chat_completion.id
                        choice = ChoiceModel(delta=DeltaModel(content=None, role='assistant'))
                        yield ChatCompletionChunkModel(id=id, choices=[choice], created=None, model=model_name)

                        for content in chat_completion.content:
                            if isinstance(content, TextBlock):
                                choice = ChoiceModel(delta=DeltaModel(content=content.text))
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=created,
                                                               model=model_name)
                            elif isinstance(content, ToolUseBlock):
                                is_tool_call = True
                                tool_call = convert_anthropic_tool_call_to_openai(content)
                                choice = ChoiceModel(delta=DeltaModel(tool_calls=[tool_call]))
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=created,
                                                               model=model_name)
                            else:
                                raise ValueError(f"Unexpected content type: {type(content)}")

                        finish_reason = 'tool_calls' if is_tool_call else 'stop'
                        choice = ChoiceModel(delta=DeltaModel(content=None), finish_reason=finish_reason)
                        yield ChatCompletionChunkModel(id=id, choices=[choice], created=None, model=model_name)

                    else:
                        async for event in chat_completion:
                            if isinstance(event, MessageStartEvent):
                                id = event.message.id
                                choice = ChoiceModel(delta=DeltaModel(content='', role='assistant'))
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=None,
                                                               model=model_name)
                            elif isinstance(event, ContentBlockDeltaEvent):
                                choice = ChoiceModel(delta=DeltaModel(content=event.delta.text))
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=None,
                                                               model=model_name)
                            elif isinstance(event, ToolsBetaContentBlockDeltaEvent):
                                is_tool_call = True
                                if isinstance(event.delta, InputJsonDelta):
                                    delta: InputJsonDelta = event.delta
                                    tool_call = {"function": {"arguments": delta.partial_json}, "index": 0}
                                    choice = ChoiceModel(delta=DeltaModel(tool_calls=[tool_call]))
                                else:
                                    delta: TextDelta = event.delta
                                    choice = ChoiceModel(delta=DeltaModel(content=delta.text))
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=None,
                                                               model=model_name)

                            elif isinstance(event, MessageStopEvent):
                                finish_reason = 'tool_calls' if is_tool_call else 'stop'
                                choice = ChoiceModel(delta=DeltaModel(content=None), finish_reason=finish_reason)
                                yield ChatCompletionChunkModel(id=id, choices=[choice], created=None,
                                                               model=model_name)
                            elif isinstance(event, ToolsBetaContentBlockStartEvent):
                                if event.content_block.type == "tool_use":
                                    function_name = event.content_block.name
                                    tool_call = {"index": 0, "id": event.content_block.id,
                                                 "type": "function",
                                                 "function": {"name": function_name, "arguments": ""}}
                                    choice = ChoiceModel(delta=DeltaModel(tool_calls=[tool_call]))
                                    yield ChatCompletionChunkModel(id=id, choices=[choice], created=None,
                                                                   model=model_name)
                            elif isinstance(event, (MessageDeltaEvent,
                                                    ContentBlockStartEvent,
                                                    ContentBlockStopEvent)):
                                pass
                            else:
                                raise ValueError(f"Unexpected event type: {type(event)}")

                    break  # Successfully processed all events, exit retry loop

                except APIStatusError as e:
                    if e.status_code == 400:
                        raise e
                    if attempt == max_attempts:
                        raise e  # Reraise the last exception after all retries have failed
                    else:
                        await asyncio.sleep(retry_delays[attempt - 1])  # Wait before retrying
                        # Note: chat_completion will be reinitialized at the start of the next loop iteration

        chat_completion = inner()
        return ChatCompletion(chat_completion)

    @property
    def chat(self):
        return type('Chat', (), {'completions': type('Completions', (), {'create': self.create})})()


class ChatCompletionResponse:
    def __init__(self, chat_completion):
        self.chat_completion = chat_completion

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            yield chunk

    async def aclose(self):
        try:
            await self.chat_completion.aclose()
        except RuntimeError:
            pass


class ChatCompletion:
    def __init__(self, chat_completion):
        self.response = ChatCompletionResponse(chat_completion)

    async def __aiter__(self):
        async for chunk in self.response:
            yield chunk


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create():
    client = AsyncAnthropicOpenAIAdapter()
    chat_completion = await client.chat.completions.create(
        model="claude-3-haiku-20240307",
        stream=True,
        messages=[{"role": "user", "content": "Short answer. 1 + 1=?"}]
    )

    received = []
    async for resp in chat_completion:
        received += [resp]

    assert received[0].model_dump()["choices"][0]["delta"]["role"] == "assistant"

    tokens = [resp.model_dump()["choices"][0]["delta"]["content"] for resp in received]

    assert tokens[0] == ''
    assert '2' in tokens
    assert tokens[-1] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_with_tools():
    available_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    client = AsyncAnthropicOpenAIAdapter()
    messages = [{"role": "user", "content": "What's the weather like in San Francisco?"}]
    chat_completion = await client.chat.completions.create(
        model="claude-3-haiku-20240307",
        stream=True,
        messages=messages,
        tools=available_tools
    )

    received = []
    async for resp in chat_completion:
        received += [resp]

    tool_calls = None
    for message in received:
        if message.choices[0].delta.tool_calls:
            tool_calls = message.choices[0].delta.tool_calls
            break

    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "get_current_weather"
    arguments = tool_calls[0].get("function", {}).get("arguments", None)
    assert arguments is not None
    assert "San Francisco" in json.loads(arguments).get("location", "")

    for message in received:
        if not message.choices[0].delta.tool_calls and not message.choices[0].delta.content:
            continue
        response = {"role": "assistant",
                    "content": message.choices[0].delta.content,
                    "tool_calls": message.choices[0].delta.tool_calls or []}
        # if not response["content"]:
        #     del response["content"]
        if not response["tool_calls"]:
            del response["tool_calls"]
        messages.append(response)

    tool_response = "23"
    messages.append({"role": "tool",
                     "tool_call_id": tool_calls[0]["id"],
                     "name": tool_calls[0]["function"]["name"],
                     "content": tool_response})

    # send the tool call return value back to anthropic
    chat_completion = await client.chat.completions.create(
        model="claude-3-haiku-20240307",
        stream=True,
        messages=messages,
        tools=available_tools
    )

    received = []
    async for resp in chat_completion:
        received += [resp]

    assert "23" in received[-2].model_dump()["choices"][0]["delta"]["content"]
