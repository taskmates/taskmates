"""Script to capture LangChain streaming chunks with tool calls and save them to a JSONL fixture file."""
import asyncio
import json
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
import os

from taskmates import root_path


@tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    return f"The weather in {location} is sunny and 72°F"


async def capture_tool_calling_chunks():
    """Capture streaming chunks from LangChain with tool calls and save to fixture file."""

    # Create fixtures directory if it doesn't exist
    fixtures_dir = root_path() / Path("tests/fixtures/api-responses")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Initialize the model with tools
    model = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        streaming=True,
        api_key=os.getenv("OPENAI_API_KEY")
    ).bind_tools([get_weather])

    # Message that should trigger a tool call
    messages = [HumanMessage(content="What's the weather in San Francisco?")]

    # Capture chunks for initial tool call
    chunks = []
    async for chunk in model.astream(messages):
        chunk_dict = chunk.dict()
        chunks.append(chunk_dict)
        print(f"Captured chunk: {chunk_dict}")

    # Save initial tool call chunks
    fixture_path = fixtures_dir / "openai_tool_call_streaming_response.jsonl"
    with open(fixture_path, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"\nSaved {len(chunks)} chunks to {fixture_path}")

    # Now simulate the full conversation with tool response
    # Get the last chunk which should have the complete tool call
    last_chunk = chunks[-1]
    tool_calls = last_chunk.get("tool_calls", [])

    if tool_calls:
        # Create the full conversation
        full_messages = [
            HumanMessage(content="What's the weather in San Francisco?"),
            AIMessage(content="", tool_calls=tool_calls),
            ToolMessage(
                content="The weather in San Francisco is sunny and 72°F",
                tool_call_id=tool_calls[0]["id"]
            )
        ]

        # Get the final response after tool execution
        final_chunks = []
        async for chunk in model.astream(full_messages):
            chunk_dict = chunk.dict()
            final_chunks.append(chunk_dict)
            print(f"Captured final chunk: {chunk_dict}")

        # Save the final response chunks
        final_fixture_path = fixtures_dir / "tool_response_streaming.jsonl"
        with open(final_fixture_path, "w") as f:
            for chunk in final_chunks:
                f.write(json.dumps(chunk) + "\n")

        print(f"\nSaved {len(final_chunks)} final chunks to {final_fixture_path}")

if __name__ == "__main__":
    asyncio.run(capture_tool_calling_chunks())
