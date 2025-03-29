import inspect
from typing import Any, Callable, Dict, List, get_type_hints

from docstring_parser import parse
from pydantic import create_model, Field, BaseConfig
from taskmates.lib.tool_schemas_.format_schema import format_schema


def tool_parameters_schema(function: Callable) -> Any:
    # Parse function signature and docstring
    sig = inspect.signature(function)
    doc = parse(function.__doc__)
    type_hints = get_type_hints(function)

    # Prepare field descriptions from the docstring
    descriptions = {p.arg_name: p.description for p in doc.params}

    # Create a dict of {arg_name: (type_hint, Field(default, description))}
    fields = {
        name: (
            type_hints.get(name, Any),
            Field(description=descriptions.get(name)) if param.default is inspect.Parameter.empty else
            Field(default=param.default, description=descriptions.get(name))
        )
        for name, param in sig.parameters.items() if param.kind not in {param.VAR_POSITIONAL, param.VAR_KEYWORD}
    }

    # Handle *args and **kwargs
    for name, param in sig.parameters.items():
        if param.kind == param.VAR_POSITIONAL:
            fields[name] = (List[Any], Field(default=[], description=descriptions.get(name)))
        elif param.kind == param.VAR_KEYWORD:
            fields[name] = (Dict[str, Any], Field(default={}, description=descriptions.get(name)))

    # Create and return the Pydantic model
    class Config(BaseConfig):
        arbitrary_types_allowed = True
        use_enum_values = True

    parameters = create_model(function.__name__, __config__=Config, **fields)
    schema = parameters.model_json_schema()
    return format_schema(schema)


def my_function(a: str, b: int = 42, *args, **kargs) -> int:
    """
    This function does something
    :param a: The first parameter
    :returns: The result
    """


def test_parameters():
    schema = tool_parameters_schema(my_function)

    assert schema == {'type': 'object',
                      'properties': {
                          'a': {
                              'type': 'string',
                              'description': 'The first parameter'
                          },
                          'b': {
                              'default': 42,
                              'type': 'integer'},
                          'args': {
                              'default': [], 'type': 'array', 'items': {}},
                          'kargs': {
                              'additionalProperties': True,
                              'default': {}, 'type': 'object'}
                      }, 'required': ['a']
                      }


def test_get_current_weather_schema():
    from taskmates.lib.tool_schemas_.tests.fixtures.get_current_weather import get_current_weather
    schema = tool_parameters_schema(get_current_weather)
    assert schema == {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
            },
            "unit": {
                "type": "string",
                'default': 'celsius',
                "enum": [
                    "celsius",
                    "fahrenheit"
                ]
            }
        },
        "required": [
            "location"
        ]
    }
