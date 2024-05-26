def split_system_message(messages):
    if messages[0]['role'] == 'system':
        system_message = messages[0]
        chat_messages = messages[1:]
    else:
        system_message = None
        chat_messages = messages
    return chat_messages, system_message
