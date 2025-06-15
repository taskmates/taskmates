def filter_messages_by_roles(messages, roles):
    return [message for message in messages if message["role"] in roles]


def filter_chat_messages(payload):
    return [message for message in payload["messages"] if
            message["role"] in ["user", "assistant"]]


def test_single_initial_message():
    payload = {
        "model": "gpt-4",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": "Hello",
            }
        ]
    }
    openai_messages = payload["messages"]
    assert openai_messages == [{"role": "user", "content": "Hello"}]


def test_message_addition_to_existing_history():
    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "user",
                "content": "Hello",
            },
            {
                "role": "assistant",
                "content": "Hi there!",
            },
            {
                "role": "user",
                "content": "What's the weather like?",
            }
        ]
    }
    openai_messages = payload["messages"]
    assert openai_messages == [{"role": "user", "content": "Hello"},
                               {"role": "assistant", "content": "Hi there!"},
                               {"role": "user", "content": "What's the weather like?"}]


def test_filter_openai_messages_with_system_role():
    messages = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "User message"}
    ]
    filtered_messages = messages
    assert filtered_messages == [{"role": "system", "content": "System message"},
                                 {"role": "user", "content": "User message"}]
