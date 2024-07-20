def compute_separator(current_markdown):
    padding = ""
    if not current_markdown.endswith("\n\n"):
        if current_markdown.endswith("\n"):
            padding = "\n"
        else:
            padding = "\n\n"
    return padding
