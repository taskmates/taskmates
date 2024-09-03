from typeguard import typechecked


@typechecked
def get_image_contents(message: dict[str, list | str | None]) -> list:
    content = message["content"]
    if not isinstance(content, list):
        return []
    images = []

    for part in content:
        if "image_url" not in part:
            continue

        image = {}
        # Extract base64 image data from URL
        image_url = part["image_url"]["url"].lstrip("data:")
        media_type, base64_image = image_url.split(",")
        # Convert to Anthropic format
        image["type"] = "image"
        image["source"] = {
            "type": "base64",
            "media_type": media_type.rstrip(";base64").replace("jpg", "jpeg"),
            "data": base64_image
        }
        images.append(image)

    return images
