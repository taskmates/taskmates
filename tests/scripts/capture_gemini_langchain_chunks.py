import asyncio
import json
import os
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from taskmates import root_path


async def capture_streaming_chunks():
    """Capture streaming chunks from Gemini LangChain and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-06-05"
    )

    # Simple test message
    messages = [HumanMessage(content="Count from 1 to 5")]

    # Capture chunks
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.model_dump()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save to fixture file
    fixture_path = fixtures_dir / "gemini_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    # Also capture a non-streaming response for comparison
    model_sync = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-06-05",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    response = await model_sync.ainvoke(messages)
    response_dict = response.model_dump()

    # Save non-streaming response
    non_streaming_path = fixtures_dir / "gemini_non_streaming_response.json"
    with open(non_streaming_path, "w") as f:
        json.dump(response_dict, f, indent=2)

    print(f"Saved non-streaming response to {non_streaming_path}")


if __name__ == "__main__":
    asyncio.run(capture_streaming_chunks())
