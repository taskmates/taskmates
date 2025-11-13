from typeguard import typechecked


@typechecked
def has_truncated_code_cell(message: dict | None) -> bool:
    if not message:
        return False

    role = message.get("role", "")

    # Messages from users or system are never resume requests
    if role in ("user", "system"):
        return False

    code_cells = message.get("code_cells", [])
    if code_cells:
        if code_cells[-1].get("truncated", False):
            return True

    return False
