def compute_and_reassign_roles(messages, recipient):
    for message in messages:
        # Don't override roles that are already set based on the message name
        if "role" in message and message["role"] in ("system", "tool"):
            continue
            
        # For messages with tool calls, they're always from the assistant
        if message.get("tool_calls") is not None:
            message["role"] = "assistant"
            continue
            
        # For all other messages, use the name as the role
        name = message.get("name", "user")
        if name in ("user", "assistant", "system", "tool"):
            message["role"] = name


# TODO
# def test_compute_and_reassign_roles():
#     messages = [
#         {"role": "user", "content": "Hello"},
#         {"role": "user", "name": "assistant1", "content": "Hi there"},
#         {"role": "user", "content": "How are you?"}
#     ]
#     participants_configs = {"user": {}, "assistant1": {"system": True}}
#
#     compute_and_reassign_roles(messages, participants_configs)
#     assert messages[1]["role"] == "assistant"
