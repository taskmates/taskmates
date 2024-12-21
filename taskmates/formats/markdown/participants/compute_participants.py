from typeguard import typechecked

from taskmates.config.load_participant_config import load_participant_config
from taskmates.formats.markdown.participants.compute_and_reassign_roles import compute_and_reassign_roles
from taskmates.formats.markdown.participants.compute_recipient import compute_recipient
from taskmates.formats.markdown.participants.process_participants import process_participants
from taskmates.logging import logger


@typechecked
async def compute_participants(taskmates_dirs, front_matter, messages) -> tuple[str | None, dict, dict]:
    front_matter_participants = front_matter.get("participants") or {}

    # Add user to participants_configs if not already present
    history_participants = {}
    for message in messages:
        if message["role"] == "user" and message["role"] not in front_matter_participants:
            name = message.get("name", message.get("role"))
            history_participants[name] = await load_participant_config(history_participants,
                                                                       name,
                                                                       taskmates_dirs)

    # Add participants from the front matter
    participants_config_raw = {**history_participants, **front_matter_participants}

    # If there is only one participant, assume it is the user
    # Add the implicit `assistant` participant
    if list(participants_config_raw.keys()) == ["user"]:
        participants_config_raw["assistant"] = {"role": "assistant"}

    participants_configs = await process_participants(participants_config_raw,
                                                      taskmates_dirs)

    # TODO: Everything below this line can be moved to a separate function
    await compute_and_assign_roles_and_recipients(messages, participants_configs, taskmates_dirs)

    recipient_name = messages[-1].get("recipient")
    recipient_role = messages[-1].get("recipient_role")

    logger.debug(f"Recipient/Role: {recipient_name}/{recipient_role}")

    return recipient_name, participants_configs.get(recipient_name, {}), participants_configs


async def compute_and_assign_roles_and_recipients(messages, participants_configs, taskmates_dirs):
    for messages_end in range(1, len(messages) + 1):
        current_messages = messages[:messages_end]
        current_message = current_messages[-1]

        recipient = compute_recipient(current_messages, participants_configs)
        current_message["recipient"] = recipient

        if current_message["role"] not in ("system", "tool"):
            name = current_message.get("name", "user")
            participants_configs[name] = await load_participant_config(participants_configs, name,
                                                                       taskmates_dirs)
            current_message["role"] = participants_configs[name].get("role", "user")

        if recipient and recipient not in participants_configs:
            participants_configs[recipient] = await load_participant_config(participants_configs,
                                                                            recipient,
                                                                            taskmates_dirs)

            current_message["recipient_role"] = participants_configs[recipient].get("role", "assistant")
        elif recipient:
            current_message["recipient_role"] = participants_configs[recipient].get("role", "user")
        else:
            current_message["recipient_role"] = None

    recipient = messages[-1].get("recipient")
    compute_and_reassign_roles(messages, recipient)
