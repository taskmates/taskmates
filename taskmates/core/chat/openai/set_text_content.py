def set_text_content(message: dict, new_content: str) -> dict:
    """
    Sets the text content of a message, handling both cases where the content
    is a string or a list of content parts.

    :param message: The message dictionary to update.
    :param new_content: The new text content to set.
    """
    if isinstance(message["content"], list):
        # Find the text part and update it
        for part in message["content"]:
            if part["type"] == "text":
                part["text"] = new_content
                break
        else:
            # If no text part is found, append a new text part
            message["content"].append({"type": "text", "text": new_content})
    else:
        # If the content is a string, simply update it
        message["content"] = new_content
    return message
