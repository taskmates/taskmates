from typeguard import typechecked


@typechecked
def get_text_content(message: dict[str, list | str | None]) -> str | None:
    content = message["content"]
    if content is None:
        return None
    elif isinstance(content, list) and all(isinstance(part, dict) for part in content):
        return "".join([part.get("text", "") for part in content if part.get("type") == "text"])
    elif isinstance(content, str):
        return content
    else:
        return ""
