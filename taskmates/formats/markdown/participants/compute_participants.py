from loguru import logger

from taskmates.environment.participants.load_participant_config import load_participant_config
from taskmates.formats.markdown.participants.compute_and_reassign_roles import compute_and_reassign_roles
from taskmates.formats.markdown.participants.compute_recipient import compute_recipient
from taskmates.formats.markdown.participants.process_participants import process_participants


async def compute_participants(taskmates_dir, front_matter, messages) -> tuple[str | None, dict]:
    front_matter_participants = front_matter.get("participants") or {}

    # add user to participants_configs if not already present
    history_participants = {}
    for message in messages:
        if message["role"] == "user" and message["role"] not in front_matter_participants:
            # history_participants[message.get("name", "user")] = {"role": "user"}
            # history_participants[message.get("name", "user")] = {"role": "user"}
            name = message.get("name", message.get("role"))
            history_participants[name] = load_participant_config(history_participants,
                                                                 name,
                                                                 taskmates_dir)

    # first_message = [message for message in messages if message["role"] in ("user", "assistant")][0]
    # first_message_mention = parse_mention(get_text_content(first_message), [])
    #
    # if first_message_mention:
    #     history_participants[first_message_mention] = load_participant_config(history_participants,
    #                                                                           first_message_mention,
    #                                                                           taskmates_dir)

    participants_config_raw = {**history_participants, **front_matter_participants}

    if list(participants_config_raw.keys()) == ["user"]:
        participants_config_raw["assistant"] = {"role": "assistant"}

    participants_configs = process_participants(participants_config_raw,
                                                taskmates_dir)

    compute_and_assign_roles_and_recipients(messages, participants_configs, taskmates_dir)

    recipient = messages[-1].get("recipient")
    logger.debug(f"Recipient: {recipient}")

    return recipient, participants_configs


def compute_and_assign_roles_and_recipients(messages, participants_configs, taskmates_dir):
    for messages_end in range(1, len(messages) + 1):
        current_messages = messages[:messages_end]
        current_message = current_messages[-1]

        recipient = compute_recipient(current_messages, participants_configs)
        current_message["recipient"] = recipient

        if current_message["role"] not in ("system", "tool"):
            name = current_message.get("name", "user")
            participants_configs[name] = load_participant_config(participants_configs, name, taskmates_dir)
            current_message["role"] = participants_configs[name].get("role", "user")

        if recipient and recipient not in participants_configs:
            participants_configs[recipient] = load_participant_config(participants_configs, recipient, taskmates_dir)
            current_message["recipient_role"] = participants_configs[recipient].get("role", "user")
        elif recipient:
            current_message["recipient_role"] = participants_configs[recipient].get("role", "user")
        else:
            current_message["recipient_role"] = None

    recipient = messages[-1].get("recipient")
    compute_and_reassign_roles(messages, recipient)
