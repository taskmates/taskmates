def compute_separator(markdown_chat):
    padding = ""
    if not markdown_chat.endswith("\n\n"):
        if markdown_chat.endswith("\n"):
            padding = "\n"
        else:
            padding = "\n\n"
    return padding
