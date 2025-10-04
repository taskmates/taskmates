def compute_trailing_newlines(content: str):
    padding = ""
    if not content.endswith("\n\n"):
        if content.endswith("\n"):
            padding = "\n"
        else:
            padding = "\n\n"
    return padding
