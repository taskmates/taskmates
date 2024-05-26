from typing import Any, Callable

from docstring_parser import parse
from taskmates.lib.tool_schemas_.tool_parameters_schema import tool_parameters_schema


def tool_schema(function: Callable) -> Any:
    doc = parse(function.__doc__)
    parameters = tool_parameters_schema(function)

    description = doc.short_description

    if description is None:
        raise ValueError(f"Function {function.__name__} must have a docstring")

    if doc.long_description:
        description += "\n" + doc.long_description

    return {
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": description,
            "parameters": parameters
        }
    }


def test_function_call_schema():
    from taskmates.lib.tool_schemas_.tests.fixtures.get_current_weather import get_current_weather
    assert tool_schema(get_current_weather) == {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": [
                            "celsius",
                            "fahrenheit"
                        ],
                        "default": "celsius"
                    }
                },
                "required": [
                    "location"
                ]
            }
        }
    }
