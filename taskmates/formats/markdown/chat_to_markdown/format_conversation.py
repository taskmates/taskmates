def format_conversation(messages) -> str:
    formatted_messages = []

    for message in messages:
        if message["role"] == "system":
            formatted_messages.append(f"**system**:\n\n {message['content']}\n")
        elif message["role"] == "user":
            formatted_messages.append(f"**user**:\n\n {message['content']}\n")
        elif message["role"] == "assistant" and message.get("function_call"):
            formatted_messages.append(f"**assistant**:\n\n {message['function_call']}\n")
        elif message["role"] == "assistant" and not message.get("function_call"):
            formatted_messages.append(f"**assistant**:\n\n {message['content']}\n")
        elif message["role"] == "function":
            formatted_messages.append(f"**function ({message['name']}):** {message['content']}\n")

    return "".join(formatted_messages)

def test_format_conversation():
    messages = [
        {"role": "system", "content": "Welcome!"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "How can I assist you today?"},
        {"role": "user", "content": "What's the weather like?"},
        {"role": "assistant", "function_call": "get_weather", "content": "It's sunny."},
        {"role": "function", "name": "get_weather", "content": "It's sunny."}
    ]

    expected_output = ("**system**:\n\n Welcome!\n"
                       "**user**:\n\n Hello\n"
                       "**assistant**:\n\n How can I assist you today?\n"
                       "**user**:\n\n What's the weather like?\n"
                       "**assistant**:\n\n get_weather\n**function (get_weather):** It's sunny.\n")

    assert format_conversation(messages) == expected_output
