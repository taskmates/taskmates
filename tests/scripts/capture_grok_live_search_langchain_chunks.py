"""Script to capture Grok LangChain streaming chunks with Live Search enabled and save them to a JSONL fixture file."""
import asyncio
import json
from pathlib import Path
from langchain_xai import ChatXAI
from langchain_core.messages import HumanMessage
import os

from taskmates import root_path


async def capture_live_search_streaming_chunks():
    """Capture streaming chunks from Grok LangChain with Live Search and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model with Live Search enabled
    model = ChatXAI(
        model="grok-4-fast-reasoning",
        temperature=0,
        streaming=True,
        search_parameters={
            "mode": "auto",
            # Optional parameters to limit scope for the fixture
            # "max_search_results": 3,
            # "from_date": "2024-10-01",  # Adjust to a recent date for relevant results
            # "to_date": "2024-10-10",
        },
        api_key=os.getenv("XAI_API_KEY")
    )

    # Prompt that should trigger Live Search for recent information
    messages = [HumanMessage(content="Provide me a digest of world news in the last week.")]

    # Capture chunks
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save to fixture file
    fixture_path = fixtures_dir / "grok_live_search_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    # Also capture a non-streaming response for comparison
    model_sync = ChatXAI(
        model="grok-4-fast-reasoning",
        temperature=0,
        streaming=False,
        search_parameters={
            "mode": "auto",
            # "max_search_results": 3,
            # "from_date": "2024-10-01",
            # "to_date": "2024-10-10",
        },
        api_key=os.getenv("XAI_API_KEY")
    )

    response = await model_sync.ainvoke(messages)
    response_dict = response.dict()

    # Save non-streaming response
    non_streaming_path = fixtures_dir / "grok_live_search_non_streaming_response.json"
    with open(non_streaming_path, "w") as f:
        json.dump(response_dict, f, indent=2)

    print(f"Saved non-streaming response to {non_streaming_path}")


if __name__ == "__main__":
    asyncio.run(capture_live_search_streaming_chunks())
