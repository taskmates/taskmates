"""Script to capture Anthropic streaming chunks with tool calls and save them to a JSONL fixture file."""
import asyncio
import json
from pathlib import Path
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

from taskmates import root_path


@tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    return f"The weather in {location} is sunny and 72°F"


async def capture_tool_calling_chunks():
    """Capture streaming chunks from Anthropic with tool calls and save to fixture file."""

    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    model = ChatAnthropic(
        model="claude-3-7-sonnet-20250219",
        temperature=0,
        streaming=True,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    ).bind_tools([get_weather])

    messages = [HumanMessage(content="What's the weather in San Francisco?")]

    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    fixture_path = fixtures_dir / "anthropic_tool_call_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    last_chunk = chunks[-1]
    tool_calls = last_chunk.get("tool_calls", [])

    if tool_calls:
        full_messages = [
            HumanMessage(content="What's the weather in San Francisco?"),
            AIMessage(content="", tool_calls=tool_calls),
            ToolMessage(
                content="The weather in San Francisco is sunny and 72°F",
                tool_call_id=tool_calls[0]["id"]
            )
        ]

        final_chunks = []
        async for chunk in model.astream(full_messages):
            chunk_dict = chunk.dict()
            final_chunks.append(chunk_dict)
            print(f"Captured final chunk: {chunk_dict}")

        final_fixture_path = fixtures_dir / "anthropic_tool_response_streaming.jsonl"
        with open(final_fixture_path, "w") as f:
            for chunk in final_chunks:
                f.write(json.dumps(chunk) + "\n")

        print(f"\nSaved {len(final_chunks)} final chunks to {final_fixture_path}")


if __name__ == "__main__":
    asyncio.run(capture_tool_calling_chunks())
