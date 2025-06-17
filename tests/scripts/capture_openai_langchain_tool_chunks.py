"""Script to capture LangChain streaming chunks with tool calls and save them to a JSONL fixture file."""
import asyncio
import json
import os
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from taskmates import root_path
from taskmates.defaults.tools.test_.get_weather import get_weather


async def capture_tool_calling_chunks():
    """Capture streaming chunks from LangChain with tool calls and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model with tools
    model = ChatOpenAI(
        model="gpt-4.1",
        temperature=0,
        streaming=True,
        api_key=os.getenv("OPENAI_API_KEY")
    ).bind_tools([get_weather])

    # Message that should trigger a tool call
    messages = [HumanMessage(content="What's the weather in San Francisco?")]

    # Capture chunks for initial tool call
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.model_dump()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save initial tool call chunks
    fixture_path = fixtures_dir / "openai_tool_call_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")


if __name__ == "__main__":
    asyncio.run(capture_tool_calling_chunks())
