"""Script to capture Ollama streaming chunks with tool calls and save them to a JSONL fixture file."""
import asyncio
import json
import os
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from taskmates import root_path
from taskmates.defaults.tools.test_.get_weather import get_weather


async def capture_tool_calling_chunks():
    """Capture streaming chunks from Ollama with tool calls and save to fixture file."""

    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    model = ChatOllama(
        model="llama4:latest",
        temperature=0,
    ).bind_tools([get_weather])

    messages = [HumanMessage(content="What's the weather in San Francisco?")]

    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    fixture_path = fixtures_dir / "ollama_llama_4_tool_call_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")


if __name__ == "__main__":
    asyncio.run(capture_tool_calling_chunks())
