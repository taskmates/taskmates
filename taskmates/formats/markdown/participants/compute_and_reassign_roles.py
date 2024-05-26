def compute_and_reassign_roles(messages, recipient):
    for message in messages:
        if message.get("name") == recipient:
            message["role"] = "assistant"

        if message.get("tool_calls") is not None:
            message["role"] = "assistant"


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
