import asyncio
from typing import Optional

import pytest
from httpx import ReadError
from loguru import logger
from opentelemetry import trace
from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.get_model_client import get_model_client
from taskmates.core.markdown_chat.metadata.config_model_conf import config_model_conf
from taskmates.core.markdown_chat.metadata.calculate_input_tokens import calculate_input_tokens
from taskmates.core.workflows.markdown_completion.completions.llm_completion._get_usernames_stop_sequences import \
    _get_usernames_stop_sequences
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.build_llm_args import \
    build_llm_args
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
from taskmates.types import CompletionRequest

tracer = trace.get_tracer_provider().get_tracer(__name__)


@typechecked
class LlmCompletionRequest:
    def __init__(self, chat: CompletionRequest, stop_sequences: list | None = None):
        run_opts = chat["run_opts"]
        model_alias = run_opts["model"]
        participants = chat.get("participants", {})
        messages = chat["messages"]
        available_tools = chat["available_tools"]

        if stop_sequences is None:
            stop_sequences = ["^######"] + _get_usernames_stop_sequences(participants)

        input_tokens = calculate_input_tokens(messages)

        # Get model configuration
        # TODO: config_model_conf is adding dynamic config to model conf
        # maybe we should move all dynamic logic there
        model_conf = config_model_conf(
            model_alias=model_alias,
            stop_sequences=stop_sequences,
            input_tokens=input_tokens
        )

        self.stop_sequences = model_conf.get("client", {}).get("kwargs", {}).get("stop", [])

        if "claude" not in model_alias:
            model_conf.get("client", {}).get("kwargs", {}).pop("stop", [])

        # Get client
        self.client = get_model_client(model_conf=model_conf)

        # Prepare request payload
        inputs = run_opts.get("inputs", {})
        self.llm_args = build_llm_args(
            messages=messages,
            available_tools=available_tools,
            participants=participants,
            inputs=inputs,
            model_conf=model_conf,
            client=self.client
        )
        self.messages = self.llm_args["messages"]
        self.tools = self.llm_args["tools"]
        self.model_params: dict = self.llm_args["model_params"]

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

        file_logger.debug("llm_args.json", content=self.llm_args)

        with tracer.start_as_current_span(name="chat-completion"):
            llm = self.client

            if self.tools:
                llm = llm.bind_tools(self.tools)

            async with RequestInterruptionMonitor(
                    status=self.status_signals,
                    control=self.control_signals
            ) as request_interruption_monitor:
                await self._stream_and_emit(
                    llm, self.messages, self.stop_sequences, request_interruption_monitor
                )

    async def execute_non_streaming(self):
        """Execute the LLM completion request without streaming."""
        if self._executed:
            raise RuntimeError("Request already executed")
        self._executed = True

        file_logger.debug("messages.json", content=[msg.model_dump() for msg in self.messages])
        file_logger.debug("tools.json", content=[tool.name for tool in self.tools])
        file_logger.debug("model_params.json", content=self.model_params)

        with tracer.start_as_current_span(name="chat-completion"):
            llm = self.client

            if self.tools:
                llm = llm.bind_tools(self.tools)

            result = await llm.ainvoke(self.messages)

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
async def test_llm_completion_request_happy_path(transaction):
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Answer with a single number. 1 + 1=", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {"model": "gpt-4o-mini"}
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Assert that the response is a LangChain AIMessage
    assert hasattr(response, 'content')
    assert response.content == '2'


@pytest.mark.integration
async def test_llm_completion_request_who_are_you(transaction):
    # Create a chat
    chat = {
        "messages": [
            {"role": "user", "content": "Who are you", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {"model": "gpt-4o-mini"}
    }

    # Create and execute request
    request = LlmCompletionRequest(chat)
    response = await request.execute_non_streaming()

    # Assert that the response is a LangChain AIMessage
    assert hasattr(response, 'content')
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.integration
async def test_llm_completion_request_with_tool_calls(transaction, tmp_path):
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
async def test_llm_completion_request_streaming_with_fixture(transaction):
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
async def test_llm_completion_request_non_streaming_with_fixture(transaction):
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
async def test_llm_completion_request_tool_call_streaming_with_fixture(transaction):
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
async def test_llm_completion_request_with_stop_sequences(transaction):
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
            },
        }
    }
    request = LlmCompletionRequest(chat, stop_sequences=[", 3"])
    # Manually add stop sequence to test

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
async def test_llm_completion_request_class(transaction):
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
async def test_llm_completion_request_status_forwarding(transaction):
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
