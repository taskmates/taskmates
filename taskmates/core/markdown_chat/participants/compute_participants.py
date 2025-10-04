from typeguard import typechecked

from taskmates.config.load_participant_config import load_participant_config
from taskmates.core.markdown_chat.participants.compute_and_reassign_roles import compute_and_reassign_roles
from taskmates.core.markdown_chat.participants.compute_recipient import compute_recipient
from taskmates.logging import logger


@typechecked
def compute_participants(front_matter, messages) -> tuple[dict, dict]:
    logger.debug("Computing participants")

    front_matter_participants = front_matter.get("participants") or {}

    participants_config_raw = front_matter_participants

    # If there is only one participant, assume it is the user
    # Add the implicit `assistant` participant
    participants_config_raw_list = list(participants_config_raw.keys())
    if participants_config_raw_list == ["user"] or participants_config_raw_list == []:
        participants_config_raw["assistant"] = {"role": "assistant"}

    participants_configs = {}

    for participant_name, participant_config in participants_config_raw.items():
        participant_config = (participant_config or {}).copy()
        loaded_config = load_participant_config(participants_config_raw, participant_name)
        participant_config.update(loaded_config)
        participants_configs[participant_name] = participant_config

    # TODO: Everything below this line can be moved into a separate function
    for messages_end in range(1, len(messages) + 1):
        current_messages = messages[:messages_end]
        current_message = current_messages[-1]

        if current_message["role"] == "user":
            name = current_message.get("name", current_message.get("role"))
            if current_message["name"] not in participants_configs:
                participants_configs[name] = load_participant_config(participants_configs, name)

        recipient = compute_recipient(current_messages, list(participants_configs.keys()))
        current_message["recipient"] = recipient

        if current_message["role"] not in ("system", "tool"):
            name = current_message.get("name", "user")
            current_message["role"] = participants_configs[name].get("role", "user")

        if recipient and recipient not in participants_configs:
            participants_configs[recipient] = load_participant_config(participants_configs, recipient)
            current_message["recipient_role"] = participants_configs[recipient].get("role", "user")
        elif recipient:
            current_message["recipient_role"] = participants_configs[recipient].get("role", "user")
        else:
            current_message["recipient_role"] = None

    recipient = messages[-1].get("recipient")
    compute_and_reassign_roles(messages, recipient)

    recipient_name = messages[-1].get("recipient")
    recipient_role = messages[-1].get("recipient_role")

    logger.debug(f"Recipient/Role: {recipient_name}/{recipient_role}")

    recipient_config = participants_configs.get(recipient_name, {}).copy() if recipient_name else {}
    if recipient_name:
        recipient_config["name"] = recipient_name

    return recipient_config, participants_configs
