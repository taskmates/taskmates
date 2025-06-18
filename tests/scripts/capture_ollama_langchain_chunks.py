"""Script to capture Ollama LangChain streaming chunks and save them to a JSONL fixture file."""
import asyncio
import json
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import os

from taskmates import root_path


async def capture_streaming_chunks():
    """Capture streaming chunks from Ollama LangChain and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model
    model = ChatOllama(
        model="llama4:latest",
        temperature=0
    )

    # Simple test message
    messages = [HumanMessage(content="Count from 1 to 5")]

    # Capture chunks
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save to fixture file
    fixture_path = fixtures_dir / "ollama_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    # Also capture a non-streaming response for comparison
    model_sync = ChatOllama(
        model="llama4:latest",
        temperature=0
    )

    response = await model_sync.ainvoke(messages)
    response_dict = response.dict()

    # Save non-streaming response
    non_streaming_path = fixtures_dir / "ollama_non_streaming_response.json"
    with open(non_streaming_path, "w") as f:
        json.dump(response_dict, f, indent=2)

    print(f"Saved non-streaming response to {non_streaming_path}")


if __name__ == "__main__":
    asyncio.run(capture_streaming_chunks())
