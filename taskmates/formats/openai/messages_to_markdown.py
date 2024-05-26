def messages_to_markdown(messages):
    text = ""
    for message in messages:
        text += f"[{message['role']}]\n"
        text += message['content'] + "\n"
        text += "\n"

    return text
