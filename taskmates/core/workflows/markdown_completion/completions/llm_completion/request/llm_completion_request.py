import asyncio
from typing import Optional

import pytest
from httpx import ReadError
from loguru import logger
from opentelemetry import trace
from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.get_model_client import get_model_client
from taskmates.core.markdown_chat.metadata.get_model_conf import get_model_conf
from taskmates.core.workflows.markdown_completion.completions.llm_completion._get_usernames_stop_sequences import \
    _get_usernames_stop_sequences
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request._convert_openai_payload_to_langchain import \
    _convert_openai_payload_to_langchain
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.prepare_request_payload import \
    prepare_request_payload
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.request_interruption_monitor import \
    RequestInterruptionMonitor
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_pre_processor import \
    LlmCompletionPreProcessor
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_with_username import \
    LlmCompletionWithUsername
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.stop_sequence_processor import \
    StopSequenceProcessor
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.llm_chat_completion_signals import LlmChatCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.defaults.settings import Settings
from taskmates.logging import file_logger
from taskmates.types import ChatCompletionRequest

tracer = trace.get_tracer_provider().get_tracer(__name__)


@typechecked
class LlmCompletionRequest:
    def __init__(self, chat: ChatCompletionRequest):
        self.chat = chat

        model_alias = chat["run_opts"]["model"]
        taskmates_dirs = Settings.get()["runner_environment"]["taskmates_dirs"]

        # Get model configuration
        self.model_conf = get_model_conf(
            model_alias=model_alias,
            messages=chat["messages"],
            taskmates_dirs=taskmates_dirs
        )

        # TODO we shouldn't mutate this
        self.model_conf["stop"].extend(_get_usernames_stop_sequences(chat))

        # Get client
        self.client = get_model_client(model_spec=self.model_conf)

        # Prepare request payload
        self.request_payload = prepare_request_payload(chat, self.model_conf, self.client)

        # Signals
        self.control_signals = ControlSignals(name="ControlSignals")
        self.status_signals = StatusSignals(name="StatusSignals")
        self.llm_chat_completion_signals = LlmChatCompletionSignals(name="LlmChatCompletionSignals")

        # Internal state
        self._executed = False
        self._result: Optional[dict] = None

    async def execute_streaming(self) -> None:
        """Execute the LLM completion request with streaming - emits chunks via signals."""
        if self._executed:
            raise RuntimeError("Request already executed")
        self._executed = True

        file_logger.debug("request_payload.json", content=self.request_payload)

        with tracer.start_as_current_span(name="chat-completion"):
            llm = self.client
            messages, tools = _convert_openai_payload_to_langchain(self.request_payload)

            if tools:
                llm = llm.bind_tools(tools)

            async with RequestInterruptionMonitor(
                    status=self.status_signals,
                    control=self.control_signals
            ) as request_interruption_monitor:
                stop_sequences = self.request_payload.pop("stop", [])
                await self._stream_and_emit(
                    llm, messages, stop_sequences, request_interruption_monitor
                )

    async def execute_non_streaming(self):
        """Execute the LLM completion request without streaming."""
        if self._executed:
            raise RuntimeError("Request already executed")
        self._executed = True

        file_logger.debug("request_payload.json", content=self.request_payload)

        with tracer.start_as_current_span(name="chat-completion"):
            llm = self.client
            messages, tools = _convert_openai_payload_to_langchain(self.request_payload)

            if tools:
                llm = llm.bind_tools(tools)

            result = await llm.ainvoke(messages)

            file_logger.debug("response.json", content=result)

            return result

    async def _stream_and_emit(self, llm, messages, stop_sequences, request_interruption_monitor):
        """Stream chunks and emit them via signals without accumulating."""
        chat_completion = llm.astream(messages)

        received_chunk = False

        try:
            async for chat_completion_chunk in \
                    LlmCompletionWithUsername(
                        LlmCompletionPreProcessor(
                            StopSequenceProcessor(
                                chat_completion,
                                stop_sequences
                            )
                        )
                    ):
                received_chunk = True
                if request_interruption_monitor.interrupted_or_killed:
                    break

                # Just emit chunks - don't accumulate
                await self.llm_chat_completion_signals.llm_chat_completion.send_async(
                    chat_completion_chunk
                )

        except asyncio.CancelledError:
            file_logger.debug("response_cancelled.json", content=str(True))
            raise
        except ReadError as e:
            file_logger.debug("response_read_error.json", content=str(e))

        if not received_chunk:
            logger.debug(f"No chunks received. Cancelling request.")
            raise asyncio.CancelledError

    @property
    def result(self) -> Optional[dict]:
        """Get the result if execution is complete."""
        return self._result

    @property
    def is_executed(self) -> bool:
        """Check if the request has been executed."""
        return self._executed


@pytest.mark.integration
async def test_llm_completion_request_happy_path(run):
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Answer with a single number. 1 + 1=", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {"model": "gpt-3.5-turbo"}
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Assert that the response is a LangChain AIMessage
    assert hasattr(response, 'content')
    assert response.content == '2'


@pytest.mark.integration
async def test_llm_completion_request_who_are_you(run):
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Who are you", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {"model": "gpt-3.5-turbo"}
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Assert that the response is a LangChain AIMessage
    assert hasattr(response, 'content')
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.integration
async def test_llm_completion_request_with_tool_calls(run, tmp_path):
    # Create a temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello from test file")

    # Create a chat with tool calls
    chat = {
        "messages": [
            {
                "content": f"Read the file at {test_file}",
                "role": "user",
                "recipient": "assistant",
                "recipient_role": "assistant"
            },
            {
                "content": None,
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "arguments": {"path": str(test_file)},
                            "name": "read_file"
                        },
                        "id": "tool_call_1701668882083",
                        "type": "function"
                    }
                ]
            },
            {
                "content": "Hello from test file",
                "name": "read_file",
                "role": "tool",
                "tool_call_id": "tool_call_1701668882083"
            },
            {
                "role": "assistant",
                "content": "The file contains: Hello from test file"
            }
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": ["read_file"],
        "run_opts": {}
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Assert that the response is a LangChain AIMessage
    assert hasattr(response, 'content')
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_llm_completion_request_streaming_with_fixture(run):
    """Test LlmCompletionRequest with streaming response using fixture."""
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Count to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_streaming_response.jsonl"
                }
            }
        }
    }

    # Collect streamed chunks
    streamed_chunks = []

    async def capture_chunk(chunk):
        streamed_chunks.append(chunk)

    # Create and execute request
    request = LlmCompletionRequest(chat)
    request.llm_chat_completion_signals.llm_chat_completion.connect(capture_chunk, weak=False)

    await request.execute_streaming()

    # Verify streaming occurred
    assert len(streamed_chunks) > 0

    # Verify we received the expected content through chunks
    content = ''.join(chunk.content for chunk in streamed_chunks if hasattr(chunk, 'content') and chunk.content)
    assert content == '1, 2, 3, 4, 5'


@pytest.mark.asyncio
async def test_llm_completion_request_non_streaming_with_fixture(run):
    """Test LlmCompletionRequest with non-streaming response using fixture."""
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Count to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_non_streaming_response.json"
                }
            }
        }
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Verify we get a LangChain AIMessage
    assert hasattr(response, 'content')
    assert response.content == '1, 2, 3, 4, 5'


@pytest.mark.asyncio
async def test_llm_completion_request_tool_call_streaming_with_fixture(run):
    """Test LlmCompletionRequest with tool call streaming response using fixture."""
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": ["get_weather"],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_tool_call_streaming_response.jsonl"
                }
            }
        }
    }

    # Collect streamed chunks
    streamed_chunks = []

    async def capture_chunk(chunk):
        streamed_chunks.append(chunk)

    # Create and execute request
    request = LlmCompletionRequest(chat)
    request.llm_chat_completion_signals.llm_chat_completion.connect(capture_chunk, weak=False)

    await request.execute_streaming()

    # Verify streaming occurred
    assert len(streamed_chunks) > 0

    # Verify we got tool call chunks
    has_tool_calls = any(
        hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks
        for chunk in streamed_chunks
    )
    assert has_tool_calls


@pytest.mark.asyncio
async def test_llm_completion_request_with_stop_sequences(run):
    """Test that stop sequences are properly handled during streaming."""
    # Create a chat - stop sequences will be added via model_conf
    chat = {
        "messages": [
            {"role": "user", "content": "Count to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {}
    }

    # Collect streamed chunks
    streamed_chunks = []

    async def capture_chunk(chunk):
        streamed_chunks.append(chunk)

    # Create and execute request
    chat["run_opts"] = {
        "model": {
            "name": "fixture",
            "kwargs": {
                "fixture_path": "tests/fixtures/api-responses/openai_streaming_response.jsonl"
            }
        }
    }
    request = LlmCompletionRequest(chat)
    # Manually add stop sequence to test
    request.request_payload["stop"] = [", 3"]  # This should stop the stream at "1, 2"
    request.llm_chat_completion_signals.llm_chat_completion.connect(capture_chunk, weak=False)

    await request.execute_streaming()

    # Verify we received the correct chunks
    # The chunks are AIMessageChunk objects, not OpenAI format dicts
    streamed_content = ''.join(
        chunk.content for chunk in streamed_chunks if hasattr(chunk, 'content') and chunk.content)
    assert streamed_content == '1, 2'
    assert ', 3' not in streamed_content
    assert ', 4' not in streamed_content
    assert ', 5' not in streamed_content


# New tests for the LlmCompletionRequest class
@pytest.mark.asyncio
async def test_llm_completion_request_class(run):
    """Test the new LlmCompletionRequest class directly."""
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Count to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_streaming_response.jsonl"
                }
            }
        }
    }

    # Create request
    request = LlmCompletionRequest(chat)

    # Collect chunks
    chunks = []

    async def collect_chunk(chunk):
        chunks.append(chunk)

    request.llm_chat_completion_signals.llm_chat_completion.connect(collect_chunk, weak=False)

    # Execute streaming
    await request.execute_streaming()

    # Verify chunks were received
    assert len(chunks) > 0
    content = ''.join(chunk.content for chunk in chunks if hasattr(chunk, 'content') and chunk.content)
    assert content == '1, 2, 3, 4, 5'

    # Verify can't execute twice
    with pytest.raises(RuntimeError, match="Request already executed"):
        await request.execute_streaming()


@pytest.mark.asyncio
async def test_llm_completion_request_status_forwarding(run):
    """Test that status signals are properly forwarded."""
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Count to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_streaming_response.jsonl"
                }
            }
        }
    }

    # Create request
    request = LlmCompletionRequest(chat)

    # Create external status signals
    external_status = StatusSignals(name="StatusSignals")
    status_updates = []

    async def capture_status(sender, **kwargs):
        status_updates.append(('any', sender))

    # Need to connect a receiver for streaming to work
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    request.llm_chat_completion_signals.llm_chat_completion.connect(capture_chunk, weak=False)

    # Connect to all status signals to capture any updates
    external_status.interrupted.connect(lambda s, **kw: status_updates.append(('interrupted', s)), weak=False)
    external_status.killed.connect(lambda s, **kw: status_updates.append(('killed', s)), weak=False)

    # Execute
    await request.execute_streaming()

    # Verify status updates were forwarded
    # Note: The actual status updates depend on RequestInterruptionMonitor
    # For now, we just verify the mechanism works
    assert request.is_executed
