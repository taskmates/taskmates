from loguru import logger
from typeguard import typechecked

from taskmates.formats.markdown.participants.parse_mention import parse_mention
from taskmates.formats.openai.get_text_content import get_text_content


@typechecked
def compute_recipient(messages, participants_configs) -> str | None:
    recipient = None

    participants = list(participants_configs.keys())
    participant_messages = [message for message in messages
                            if message["role"] not in ("system", "tool")
                            and message.get("name") not in ("cell_output",)
                            ]

    if not participant_messages:
        return None

    last_participant_message = participant_messages[-1]
    last_participant_message.setdefault("name", last_participant_message.get("role"))
    last_participant_message_role = participants_configs.get(last_participant_message["name"], {}).get("role")

    mention = None
    if last_participant_message is not None:
        # parse @mentions
        mention = parse_mention(get_text_content(last_participant_message), participants)

    is_self_mention = mention == messages[-1].get("name")
    is_tool_reply = messages[-1]["role"] == "tool"
    is_code_cell_reply = messages[-1].get("name") == "cell_output"

    if mention and not is_self_mention and not is_tool_reply:
        recipient = mention

    # code cell/tool call: resume conversation with caller
    elif is_tool_reply or is_code_cell_reply:
        recipient = last_participant_message["name"]

    # code cell/tool caller: resume conversation with requester
    elif len(messages) > 2 and (messages[-2]["role"] == "tool" or messages[-2].get("name") == "cell_output"):
        tool_calling_message = participant_messages[-2]
        recipient = tool_calling_message["recipient"]

    # alternating participants
    elif len(participants) == 2 and "user" in participants:
        recipient = [participant for participant in participants
                     if participant != last_participant_message.get("name", last_participant_message.get("role"))][0]

    # default: assistant reply to request
    elif last_participant_message_role == "assistant" and len(participant_messages) > 1:
        recipient = participant_messages[-2]["name"]

    # re-initiate conversation
    elif last_participant_message_role == "user":
        # search last assistant message
        for message in reversed(participant_messages):
            if message["name"] != last_participant_message["name"]:
                recipient = message["name"]
                break

    logger.debug(f"Computed recipient: {recipient}")
    return recipient


# Test cases

def test_implicit_assistant():
    messages = [
        {"role": "user", "content": "Hello"},
    ]
    participants_configs = {"user": {}, "assistant": {}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient == "assistant"


def test_mention_reply():
    messages = [
        {"role": "user", "name": "user", "content": "Hello", "recipient": "assistant"},
        {"role": "user", "name": "dave", "content": "Hey @alice how much is 1 + 1?", "recipient": "alice"},
        {"role": "assistant", "name": "alice", "content": "2"},

    ]
    participants_configs = {"user": {}, "assistant": {}, "alice": {"role": "assistant"}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient == "dave"


def test_tool_resume():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "name": "assistant1", "content": "Hi there"},
        {"role": "tool", "content": "Running tool..."}
    ]
    participants_configs = {"user": {}, "assistant1": {"system": True}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient == "assistant1"


def test_mention():
    messages = [
        {"role": "user", "content": "Hello @assistant2"},
    ]
    participants_configs = {"user": {}, "assistant1": {"system": True}, "assistant2": {}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient == "assistant2"


def test_alternating():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "name": "assistant1", "content": "Hi there"},
        {"role": "user", "content": "How are you?"}
    ]
    participants_configs = {"user": {}, "assistant1": {"system": True}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient == "assistant1"


def test_unknown():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "name": "assistant1", "content": "Hi there"},
        {"role": "user", "content": "How are you?"}
    ]
    participants_configs = {"user": {}, "assistant1": {"system": True}, "assistant2": {"system": True}}

    recipient = compute_recipient(messages, participants_configs)
    assert recipient is None
