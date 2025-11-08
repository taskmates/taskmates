"""Script to capture Anthropic LangChain streaming chunks with thinking enabled and save them to a JSONL fixture file."""
import asyncio
import json
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
import os

from taskmates import root_path


async def capture_streaming_chunks_with_thinking():
    """Capture streaming chunks from Anthropic LangChain with thinking enabled and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model with thinking enabled
    model = ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=1,
        streaming=True,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=5000,
        thinking={"type": "enabled", "budget_tokens": 2000},
    )

    # Simple test message
    messages = [HumanMessage(content="Count from 1 to 5")]

    # Capture streaming chunks
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save to fixture file
    fixture_path = fixtures_dir / "anthropic_thinking_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    # Also capture a non-streaming response for comparison
    model_sync = ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=1,
        streaming=False,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=5000,
        thinking={"type": "enabled", "budget_tokens": 2000},
    )

    response = await model_sync.ainvoke(messages)
    response_dict = response.dict()

    # Save non-streaming response
    non_streaming_path = fixtures_dir / "anthropic_thinking_non_streaming_response.json"
    with open(non_streaming_path, "w") as f:
        json.dump(response_dict, f, indent=2)

    print(f"Saved non-streaming response to {non_streaming_path}")


if __name__ == "__main__":
    asyncio.run(capture_streaming_chunks_with_thinking())
