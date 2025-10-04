import re
from typing import Dict

import pytest
from icecream import ic
from langchain_core.messages import AIMessageChunk
from typeguard import typechecked

from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals


def snake_case_to_title_case(text: str) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), text.replace('_', ' ')).title()


@typechecked
class LlmCompletionMarkdownAppender:
    def __init__(self,
                 recipient: str,
                 last_tool_call_id: int,
                 is_resume_request: bool,
                 execution_environment_signals: ExecutionEnvironmentSignals):
        self.recipient = recipient
        self.last_tool_call_id = last_tool_call_id
        self.execution_environment_signals = execution_environment_signals
        self.role = None
        self.name = None
        self.is_resume_request = is_resume_request
        self._tool_call_accumulator = {}
        self._content_buffer = ""
        self._annotations = []
        self._citation_counter = 0
        self._tool_calls_finalized = False

    async def process_chat_completion_chunk(self, chunk: AIMessageChunk):
        # role
        await self.on_received_role(chunk)

        # annotations
        await self.on_received_annotations(chunk)

        # text
        await self.on_received_content(chunk)

        # tool calls
        await self.on_received_tool_calls(chunk)

        # Check if this is the final chunk
        finish_reason = chunk.response_metadata.get("finish_reason")
        status = chunk.response_metadata.get("status")
        if finish_reason == "stop" or status == "completed":
            await self.on_completion()

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
        status = chunk.response_metadata.get("status")
        # Also check for STOP finish_reason with tool_call_accumulator (for Gemini)
        if finish_reason == "tool_calls" or stop_reason == "tool_use" or (status == "completed" and self._tool_call_accumulator) or (finish_reason == "STOP" and self._tool_call_accumulator):
            # Output all accumulated tool calls in order of index
            sorted_calls = sorted(self._tool_call_accumulator.items())

            for idx, (index, acc) in enumerate(sorted_calls):
                # Handle None index (e.g., from Gemini) by using idx
                code_cell_id = self.last_tool_call_id + 1 + (index if index is not None else idx)
                if idx == 0:
                    await self.append("\n\n###### Steps\n\n")
                else:
                    await self.append("`\n")
                function_title = snake_case_to_title_case(acc["function_name"])
                tool_call_completion = f"- {function_title} [{code_cell_id}] `"
                await self.append(tool_call_completion)
                # Escape backticks in arguments
                escaped_arguments = acc["arguments"].replace("`", "\\`")
                await self.append(escaped_arguments)
            await self.append("`\n\n")
            self._tool_call_accumulator.clear()
            self._tool_calls_finalized = True

    async def append_tool_calls(self, tool_call_json: Dict):
        # Deprecated: now handled in on_received_tool_calls
        pass

    async def on_received_content(self, chunk: AIMessageChunk):
        content = chunk.content
        if content:
            # Don't append content if tool calls have been finalized
            if self._tool_calls_finalized:
                return

            # Don't append content if this chunk has tool_call_chunks (it's likely tool arguments)
            tool_call_chunks = chunk.tool_call_chunks if hasattr(chunk, "tool_call_chunks") else []
            if tool_call_chunks:
                return

            # Handle both string and list content
            if isinstance(content, str):
                self._content_buffer += content
                await self.append(content)
            elif isinstance(content, list):
                # Extract text from list content
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text", "")
                        self._content_buffer += text
                        await self.append(text)

    async def on_received_role(self, chunk: AIMessageChunk):
        if not self.role:
            self.role = "assistant"
            recipient = self.recipient
            if not self.is_resume_request:
                await self.execution_environment_signals.response.send_async(sender="responder", value=f"**{recipient}>** ")

    async def append(self, text: str):
        await self.execution_environment_signals.response.send_async(sender="response", value=text)

    async def on_received_annotations(self, chunk: AIMessageChunk):
        # Check for annotations in the custom attribute
        if hasattr(chunk, 'annotations') and chunk.annotations:
            self._annotations.extend(chunk.annotations)

    async def on_completion(self):
        # If we have annotations, format them as markdown citations
        if self._annotations:
            await self.append_citations()

    async def append_citations(self):
        # Sort annotations by start_index to process them in order
        sorted_annotations = sorted(self._annotations, key=lambda a: a.get('start_index', 0))

        # Group annotations by URL to avoid duplicates
        unique_citations = {}
        citation_map = {}  # Maps (start, end) to citation number

        for ann in sorted_annotations:
            url = ann.get('url', '')
            title = ann.get('title', '')
            start = ann.get('start_index', 0)
            end = ann.get('end_index', 0)

            if url not in unique_citations:
                self._citation_counter += 1
                unique_citations[url] = {
                    'number': self._citation_counter,
                    'title': title,
                    'url': url
                }

            citation_map[(start, end)] = unique_citations[url]['number']

        # Append citations section
        if unique_citations:
            await self.append("\n\n---\n\n### References\n\n")
            for citation in sorted(unique_citations.values(), key=lambda c: c['number']):
                await self.append(f"[{citation['number']}] {citation['title']}: {citation['url']}\n\n")




@pytest.mark.asyncio
async def test_openai_web_search_tool_call_completion():
    """Reproduces the error when processing OpenAI web search tool call streaming responses with annotations."""
    import os
    import json
    from langchain_core.messages import AIMessageChunk
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_pre_processor import \
        LlmCompletionPreProcessor

    # Create a test signals class to capture outputs
    class TestExecutionEnvironmentSignals(ExecutionEnvironmentSignals):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.responder_outputs = []
            self.response_outputs = []

            async def capture_responder(sender, value):
                self.responder_outputs.append(value)

            async def capture_response(sender, value):
                self.response_outputs.append(value)

            self.response.connect(capture_responder, sender="responder", weak=False)
            self.response.connect(capture_response, sender="response", weak=False)

    # Load OpenAI web search fixture
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "../../../../../../../tests/fixtures/api-responses/openai_web_search_tool_call_streaming_response.jsonl"
    )
    fixture_path = os.path.normpath(fixture_path)

    with open(fixture_path, "r") as f:
        lines = f.readlines()

    chunks = [AIMessageChunk(**json.loads(line)) for line in lines]

    # Create test signals
    execution_environment_signals = TestExecutionEnvironmentSignals(name="TestExecutionEnvironmentSignals")

    appender = LlmCompletionMarkdownAppender(
        recipient="assistant",
        last_tool_call_id=0,
        is_resume_request=False,
        execution_environment_signals=execution_environment_signals
    )

    # Process chunks through pre-processor first
    async def chunk_stream():
        for chunk in chunks:
            yield chunk

    pre_processor = LlmCompletionPreProcessor(chunk_stream())

    # Process all chunks - this should now work without errors
    async for processed_chunk in pre_processor:
        await appender.process_chat_completion_chunk(processed_chunk)

    # Verify the responder was called with the assistant prompt
    assert "**assistant>** " in execution_environment_signals.responder_outputs

    # Collect all the appended text
    appended_text = "".join(execution_environment_signals.response_outputs)

    # Should contain the text response about AI news
    assert "Here are some of the latest developments in artificial intelligence" in appended_text

    # Should contain some of the AI news content
    assert "Meta" in appended_text
    assert "AI" in appended_text

    # Should contain the references section with citations
    assert "### References" in appended_text
    assert "Axios AM: What if they're right?" in appended_text
    assert "https://www.axios.com/" in appended_text
