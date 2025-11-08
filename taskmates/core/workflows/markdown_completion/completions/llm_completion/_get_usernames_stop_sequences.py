from typing import List


def _get_usernames_stop_sequences(participants: dict) -> List[str]:
    user_participants = ["user"]
    for name, config in participants.items():
        if config["role"] == "user" and name not in user_participants:
            user_participants.append(name)
    username_stop_sequences = [f"\n**{u}>** " for u in user_participants]
    return username_stop_sequences
