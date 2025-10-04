def get_available_tools(front_matter: dict, recipient_config: dict) -> dict:
    if recipient_config.get("tools") is not None:
        return recipient_config["tools"]

    tools_dict = {}

    for tool, tool_tools_dict in front_matter.get("tools", {}).items():
        tools_dict[tool] = None
        if tool_tools_dict is not None:
            tools_dict[tool] = tool_tools_dict

    return tools_dict


# Pytest tests
def test_substitute_tools_with_user_message():
    front_matter = {"tools": {"my_function": None,
                              "my_other_function": None,
                              "my_third_function": None}}
    tools_dict = get_available_tools(front_matter, {})
    assert tools_dict == {'my_function': None, 'my_other_function': None, 'my_third_function': None}


def test_substitute_tools_with_tools_dict():
    front_matter = {"tools": {"my_function": None,
                              'my_function_with_tools_dict': {"key": "value"}}}

    tools_dict = get_available_tools(front_matter, {})
    assert tools_dict == {'my_function': None, 'my_function_with_tools_dict': {'key': 'value'}}
