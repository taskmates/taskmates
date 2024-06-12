import pytest


def convert_openai_tools_to_anthropic(tools) -> list[dict]:
    anthropic_tools = []
    for tool in tools:
        anthropic_tool = {
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "input_schema": tool["function"]["parameters"]
        }
        anthropic_tools.append(anthropic_tool)
    return anthropic_tools


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convert_openai_tools_to_anthropic():
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    anthropic_tools = convert_openai_tools_to_anthropic(openai_tools)

    assert anthropic_tools == [
        {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        }
    ]
