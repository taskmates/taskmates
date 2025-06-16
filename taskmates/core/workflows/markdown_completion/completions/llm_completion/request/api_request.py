import asyncio
import json
from typing import Callable

import pytest
from httpx import ReadError
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage, BaseMessage, ToolCall
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI
from loguru import logger
from opentelemetry import trace
from typeguard import typechecked

from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.request_interruption_monitor import \
    RequestInterruptionMonitor
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_pre_processor import \
    LlmCompletionPreProcessor
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_with_username import \
    LlmCompletionWithUsername
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.streamed_response import \
    StreamedResponse
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.llm_completion_signals import LlmCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.lib.matchers_ import matchers
from taskmates.logging import file_logger

tracer = trace.get_tracer_provider().get_tracer(__name__)


def convert_function_to_langchain_tool(func: Callable) -> BaseTool:
    """Convert a raw function to a LangChain tool using StructuredTool.from_function."""
    return StructuredTool.from_function(func=func)


def convert_openai_payload(payload: dict) -> tuple[list[BaseMessage], list[BaseTool]]:
    # Map OpenAI role strings to LangChain message classes
    role_map = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
        "tool": ToolMessage,
    }

    # Convert message list
    messages = []
    for msg in payload["messages"]:
        content = msg["content"] or ""

        raw_tool_calls = msg.get("tool_calls", [])
        tool_calls = []

        for tool_call in raw_tool_calls:
            id = tool_call["id"]
            type = tool_call["type"]
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            tool_calls.append(ToolCall(name=name, args=args, id=id, type=type))

        msg_args = dict(
            content=content,
            tool_calls=tool_calls
        )

        if "tool_call_id" in msg:
            msg_args["tool_call_id"] = msg.get("tool_call_id")

        message = role_map[msg["role"]](**msg_args)
        messages.append(message)

    # Convert raw functions to LangChain tools
    raw_tools = payload.get("tools", [])
    tools: list[BaseTool] = []
    for tool_func in raw_tools:
        if callable(tool_func):
            langchain_tool = convert_function_to_langchain_tool(tool_func)
            tools.append(langchain_tool)

    return messages, tools


@typechecked
async def api_request(
        client: BaseChatModel,
        request_payload: dict,
        control_signals: ControlSignals,
        status_signals: StatusSignals,
        chat_completion_signals: LlmCompletionSignals
) -> dict:
    streamed_response = StreamedResponse()

    file_logger.debug("request_payload.json", content=request_payload)

    with tracer.start_as_current_span(name="chat-completion"):
        async with RequestInterruptionMonitor(status=status_signals,
                                              control=control_signals) as request_interruption_monitor:
            messages, tools = convert_openai_payload(request_payload)

            llm = client

            if "gpt" in (getattr(llm, "model_name", "") or getattr(llm, "model", "")):
                webtool = {"type": "web_search_preview"}
                tools.append(webtool)
            if tools:
                llm = llm.bind_tools(tools)

            force_stream = bool(chat_completion_signals.chat_completion.receivers)

            # TODO: handle stop_sequences manually
            # stop_sequences = request_payload.pop("stop", [])
            # "stop": ["\n######"],
            # model_conf["stop"].extend(self.get_usernames_stop_sequences(chat))


            if request_payload.get("stream", force_stream):
                chat_completion = llm.astream(messages)
                chat_completion_signals.chat_completion.connect(streamed_response.accept, weak=False)

                received_chunk = False

                try:
                    async for chat_completion_chunk in \
                            LlmCompletionWithUsername(LlmCompletionPreProcessor(chat_completion)):
                        received_chunk = True
                        if request_interruption_monitor.interrupted_or_killed:
                            break
                        await chat_completion_signals.chat_completion.send_async(chat_completion_chunk)

                except asyncio.CancelledError:
                    file_logger.debug("response_cancelled.json", content=str(True))
                    raise
                except ReadError as e:
                    file_logger.debug("response_read_error.json", content=str(e))

                response = streamed_response.payload
                if not response.get('choices'):
                    logger.debug(f"Empty response['choices'].. Cancelling request. received_chunk={received_chunk}")
                    raise asyncio.CancelledError

            else:
                # For non-streaming, use ainvoke to get a single response
                result = await llm.ainvoke(messages)
                # Convert LangChain response to OpenAI format
                response = {
                    'choices': [{
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': result.content,
                            'tool_calls': result.tool_calls if hasattr(result,
                                                                       'tool_calls') and result.tool_calls else None
                        },
                        'finish_reason': 'tool_calls' if hasattr(result, 'tool_calls') and result.tool_calls else 'stop'
                    }],
                    'object': 'chat.completion',
                    'model': getattr(result, 'response_metadata', {}).get('model_name', 'unknown'),
                    'id': getattr(result, 'id', None)
                }
                # Add any additional metadata from response_metadata
                if hasattr(result, 'response_metadata'):
                    response.update(result.response_metadata)

    file_logger.debug("response.json", content=response)

    finish_reason = response['choices'][0]['finish_reason']
    logger.debug(f"Finish Reason: {finish_reason}")

    if finish_reason not in ('stop', 'tool_calls'):
        raise Exception(f"API response has been truncated: finish_reason={finish_reason}")

    return response


@pytest.mark.integration
async def test_api_request_happy_path(run):
    # Define the model configuration and parameters as per your actual use case
    request_payload = {
        "model": "gpt-3.5-turbo",
        "stream": True,
        "messages": [
            {"role": "user", "content": "Answer with a single number. 1 + 1="},
        ]
    }

    expected = {'choices': [{'finish_reason': 'stop',
                             'index': 0,
                             'message': {'content': '2', 'role': 'assistant'}}],
                'finish_reason': 'stop',
                'id': matchers.any_string,
                'model_name': 'gpt-3.5-turbo-0125',
                'object': 'chat.completion',
                'service_tier': 'default'}

    # Call the api_request function with the defined parameters
    client = ChatOpenAI(model="gpt-3.5-turbo")
    response = await api_request(client, request_payload,
                                 run.signals["control"],
                                 run.signals["status"],
                                 run.signals["chat_completion"]
                                 )

    # Assert that the response matches the new AIMessageChunk protocol
    assert response == expected


@pytest.mark.integration
async def test_api_request_who_are_you(run):
    # Define the model configuration and parameters as per your actual use case
    request_payload = {
        "model": "gemini-2.5-pro-exp-03-25",
        "stream": True,
        "messages": [
            {"role": "user", "content": "Who are you"},
        ]
    }

    # Call the api_request function with the defined parameters
    client = ChatOpenAI(model="gpt-3.5-turbo")
    response = await api_request(client, request_payload,
                                 run.signals["control"],
                                 run.signals["status"],
                                 run.signals["chat_completion"]
                                 )

    # Assert the response has correct OpenAI format with expected fields
    assert response == {
        'choices': [{
            'finish_reason': 'stop',
            'index': 0,
            'message': {
                'content': matchers.any_string,
                'role': 'assistant'
            }
        }],
        'finish_reason': 'stop',
        'id': matchers.any_string,
        'model_name': matchers.any_string,
        'object': 'chat.completion',
        'service_tier': matchers.any_string
    }


@pytest.mark.integration
async def test_api_request_with_tool_calls(run):
    # Define the complex payload based on the JSON you provided
    request_payload = {
        "model": "gpt-3.5-turbo",
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 4096,
        "messages": [
            {
                "content": "what is on https://asurprisingimage.com?\n",
                "role": "user"
            },
            {
                "content": None,
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "arguments": "{\"url\":\"https://asurprisingimage.com\"}",
                            "name": "visit_page"
                        },
                        "id": "tool_call_1701668882083",
                        "type": "function"
                    }
                ]
            },
            {
                "content": "[cat.jpeg](..%2F..%2F..%2F..%2F..%2FDownloads%2Fcat.jpeg)\n",
                "name": "visit_page",
                "role": "tool",
                "tool_call_id": "tool_call_1701668882083"
            },
            {
                "role": "assistant",
                "content": "![[/Users/ralphus/Downloads/cat.jpeg]]\n\nI can see a cat in the image."
            }
        ],
        "tools": [{
            "type": "function",
            "name": "visit_page",
            "description": "Visits a page",
            "parameters": {
                "properties": {
                    "url": {
                        "description": "the url"
                    }
                },
                "required": ["url"],
                "type": "object"
            }
        }]
    }

    # Call the api_request function with the defined parameters
    contexts = RUN.get().context
    client = ChatOpenAI(model="gpt-3.5-turbo")
    response = await api_request(client,
                                 request_payload,
                                 run.signals["control"],
                                 run.signals["status"],
                                 run.signals["chat_completion"]
                                 )

    # Assert the response conforms to OpenAI format
    assert response == {
        'choices': [{
            'finish_reason': 'stop',
            'index': 0,
            'message': {
                'content': matchers.any_string,
                'role': 'assistant'
            }
        }],
        'finish_reason': 'stop',
        'id': matchers.any_string,
        'model_name': matchers.any_string,
        'object': 'chat.completion',
        'service_tier': matchers.any_string
    }


@pytest.mark.asyncio
async def test_api_request_streaming_with_fixture(run):
    """Test api_request with streaming response using fixture."""
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import \
        FixtureChatModel

    # Use the streaming fixture
    client = FixtureChatModel(fixture_path="tests/fixtures/api-responses/streaming_response.jsonl")

    request_payload = {
        "model": "fixture-model",
        "stream": True,
        "messages": [
            {"role": "user", "content": "Count to 5"},
        ]
    }

    # Collect streamed chunks
    streamed_chunks = []

    async def capture_chunk(chunk):
        streamed_chunks.append(chunk)

    run.signals["chat_completion"].chat_completion.connect(capture_chunk, weak=False)

    response = await api_request(
        client,
        request_payload,
        run.signals["control"],
        run.signals["status"],
        run.signals["chat_completion"]
    )

    # Verify the conversion produces correct OpenAI format
    assert response == {
        'choices': [{
            'finish_reason': 'stop',
            'index': 0,
            'message': {
                'content': '1, 2, 3, 4, 5',
                'role': 'assistant'
            }
        }],
        'finish_reason': 'stop',
        'id': matchers.any_string,
        'model_name': matchers.any_string,
        'object': 'chat.completion',
        'service_tier': 'default'
    }

    # Verify streaming occurred
    assert len(streamed_chunks) > 0


@pytest.mark.asyncio
async def test_api_request_non_streaming_with_fixture(run):
    """Test api_request with non-streaming response using fixture."""
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import \
        FixtureChatModel

    # Use the non-streaming fixture
    client = FixtureChatModel(fixture_path="tests/fixtures/api-responses/non_streaming_response.json")

    request_payload = {
        "model": "fixture-model",
        "stream": False,
        "messages": [
            {"role": "user", "content": "Count to 5"},
        ]
    }

    response = await api_request(
        client,
        request_payload,
        run.signals["control"],
        run.signals["status"],
        run.signals["chat_completion"]
    )

    # Verify the conversion produces correct OpenAI format
    assert response == matchers.dict_containing({
        'choices': [{
            'finish_reason': 'stop',
            'index': 0,
            'message': {
                'content': '1, 2, 3, 4, 5',
                'role': 'assistant',
                'tool_calls': None
            }
        }],
        'object': 'chat.completion',
        'model_name': matchers.any_string,
        'id': matchers.any_string,
        'service_tier': 'default'
    })


@pytest.mark.asyncio
async def test_api_request_tool_call_streaming_with_fixture(run):
    """Test api_request with tool call streaming response using fixture."""
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import \
        FixtureChatModel

    # Use the tool call streaming fixture
    client = FixtureChatModel(fixture_path="tests/fixtures/api-responses/openai_tool_call_streaming_response.jsonl")

    # Define a dummy weather tool
    def get_weather(location: str) -> str:
        """Get the weather for a location."""
        return f"The weather in {location} is sunny and 72°F"

    request_payload = {
        "model": "fixture-model",
        "stream": True,
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ],
        "tools": [get_weather]
    }

    # Collect streamed chunks
    streamed_chunks = []

    async def capture_chunk(chunk):
        streamed_chunks.append(chunk)

    run.signals["chat_completion"].chat_completion.connect(capture_chunk, weak=False)

    response = await api_request(
        client,
        request_payload,
        run.signals["control"],
        run.signals["status"],
        run.signals["chat_completion"]
    )

    # Verify the conversion produces correct OpenAI format with tool calls
    assert response == {
        'choices': [{
            'finish_reason': 'tool_calls',
            'index': 0,
            'message': {
                'content': None,
                'role': 'assistant',
                'tool_calls': [{
                    'function': {
                        'name': 'get_weather',
                        'arguments': matchers.json_matching('{"location": "San Francisco"}')
                    },
                    'id': 'call_6NoPEzeAUH339GjGUxpcOgbX',
                    'type': 'function'
                }]
            }
        }],
        'finish_reason': 'tool_calls',
        'id': matchers.any_string,
        'model_name': matchers.any_string,
        'object': 'chat.completion',
        'service_tier': 'default'
    }

    # Verify streaming occurred
    assert len(streamed_chunks) > 0
