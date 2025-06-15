import re
from typing import Dict

import pytest
from langchain_core.messages import AIMessageChunk
from typeguard import typechecked

from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals


def snake_case_to_title_case(text: str) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), text.replace('_', ' ')).title()


@typechecked
class LlmCompletionMarkdownAppender:
    def __init__(self,
                 recipient: str,
                 last_tool_call_id: int,
                 is_resume_request: bool,
                 markdown_completion_signals: MarkdownCompletionSignals):
        self.recipient = recipient
        self.last_tool_call_id = last_tool_call_id
        self.markdown_completion_signals = markdown_completion_signals
        self.role = None
        self.name = None
        self.is_resume_request = is_resume_request
        self._tool_call_accumulator = {}

    async def process_chat_completion_chunk(self, chunk: AIMessageChunk):
        # role
        await self.on_received_role(chunk)

        # text
        await self.on_received_content(chunk)

        # tool calls
        await self.on_received_tool_calls(chunk)

    async def on_received_tool_calls(self, chunk: AIMessageChunk):
        # Use tool_call_chunks for streaming responses
        tool_call_chunks = chunk.tool_call_chunks or []

        for tool_call_chunk in tool_call_chunks:
            index = tool_call_chunk.get("index", 0)
            # Use only index as key since tool_call_id can be None in subsequent chunks
            key = index

            if key not in self._tool_call_accumulator:
                # Initialize with the first chunk's data (which should have the function name)
                self._tool_call_accumulator[key] = {
                    "function_name": tool_call_chunk.get("name", ""),
                    "arguments": "",
                    "tool_call_id": tool_call_chunk.get("id"),
                    "tool_call_json": tool_call_chunk,
                }

            # Accumulate arguments from all chunks
            args = tool_call_chunk.get("args", "")
            if args:
                self._tool_call_accumulator[key]["arguments"] += args

            # Update tool_call_id if we get a non-None value
            if tool_call_chunk.get("id") is not None:
                self._tool_call_accumulator[key]["tool_call_id"] = tool_call_chunk.get("id")

        # wrap up tool calls
        finish_reason = chunk.response_metadata.get("finish_reason")
        stop_reason = chunk.response_metadata.get("stop_reason")
        if finish_reason == "tool_calls" or stop_reason == "tool_use":
            # Output all accumulated tool calls in order of index
            sorted_calls = sorted(self._tool_call_accumulator.items())

            for idx, (index, acc) in enumerate(sorted_calls):
                code_cell_id = self.last_tool_call_id + 1 + index
                if idx == 0:
                    await self.append("\n\n###### Steps\n\n")
                else:
                    await self.append("`\n")
                function_title = snake_case_to_title_case(acc["function_name"])
                tool_call_completion = f"- {function_title} [{code_cell_id}] `"
                await self.append(tool_call_completion)
                await self.append(acc["arguments"])
            await self.append("`\n\n")
            self._tool_call_accumulator.clear()

    async def append_tool_calls(self, tool_call_json: Dict):
        # Deprecated: now handled in on_received_tool_calls
        pass

    async def on_received_content(self, chunk: AIMessageChunk):
        content = chunk.content
        if content:
            await self.append(content)

    async def on_received_role(self, chunk: AIMessageChunk):
        if not self.role:
            self.role = "assistant"
            recipient = self.recipient
            if not self.is_resume_request:
                await self.markdown_completion_signals.responder.send_async(f"**{recipient}>** ")

    async def append(self, text: str):
        await self.markdown_completion_signals.response.send_async(text)


@pytest.mark.asyncio
async def test_anthropic_tool_call_completion():
    """Allows the user to trigger tool calls from Anthropic streaming responses."""
    import os
    import json
    from langchain_core.messages import AIMessageChunk
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_pre_processor import \
        LlmCompletionPreProcessor

    # Create a test signals class to capture outputs
    class TestMarkdownCompletionSignals(MarkdownCompletionSignals):
        def __init__(self):
            super().__init__()
            self.responder_outputs = []
            self.response_outputs = []

            async def capture_responder(sender, **kwargs):
                self.responder_outputs.append(sender)

            async def capture_response(sender, **kwargs):
                self.response_outputs.append(sender)

            self.responder.connect(capture_responder, weak=False)
            self.response.connect(capture_response, weak=False)

    # Load Anthropic fixture
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "../../../../../../../tests/fixtures/api-responses/anthropic_tool_call_streaming_response.jsonl"
    )
    fixture_path = os.path.normpath(fixture_path)

    with open(fixture_path, "r") as f:
        lines = f.readlines()

    chunks = [AIMessageChunk(**json.loads(line)) for line in lines]

    # Create test signals
    markdown_completion_signals = TestMarkdownCompletionSignals()

    appender = LlmCompletionMarkdownAppender(
        recipient="assistant",
        last_tool_call_id=0,
        is_resume_request=False,
        markdown_completion_signals=markdown_completion_signals
    )

    # Process chunks through pre-processor first
    async def chunk_stream():
        for chunk in chunks:
            yield chunk

    pre_processor = LlmCompletionPreProcessor(chunk_stream())

    # Process all chunks
    async for processed_chunk in pre_processor:
        await appender.process_chat_completion_chunk(processed_chunk)

    # Verify the responder was called with the assistant prompt
    assert "**assistant>** " in markdown_completion_signals.responder_outputs

    # Collect all the appended text
    appended_text = "".join(markdown_completion_signals.response_outputs)

    # Should contain the text response
    assert "I'll check the current weather in San Francisco for you." in appended_text

    # Should contain the tool call markdown
    assert "###### Steps" in appended_text
    assert "- Get Weather [2] `" in appended_text
    assert '{"location": "San Francisco"}' in appended_text
