from taskmates.types import ChatCompletionRequest


def has_truncated_code_cell(chat: ChatCompletionRequest) -> bool:
    if not chat["messages"]:
        return False

    last_message = chat["messages"][-1]
    role = last_message.get("role", "")

    # Messages from users or system are never resume requests
    if role in ("user", "system"):
        return False

    code_cells = last_message.get("code_cells", [])
    if code_cells:
        if code_cells[-1].get("truncated", False):
            return True

    return False
