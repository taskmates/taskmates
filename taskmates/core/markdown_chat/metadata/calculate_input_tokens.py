import copy
import json

from typeguard import typechecked

from taskmates.lib.openai_.count_tokens import count_tokens


@typechecked
def calculate_input_tokens(messages: list):
    # Count images and prepare payload for token counting
    images = 0
    approximate_payload = copy.deepcopy(messages)
    for message in approximate_payload:
        if isinstance(message.get("content", None), list):
            for part in message.get("content", []):
                if part["type"] != "text":
                    del part["image_url"]
                    images += 1

    # Calculate available tokens: context window - input tokens - image tokens - safety buffer
    input_tokens = count_tokens(json.dumps(approximate_payload, ensure_ascii=False))
    image_tokens = images * 100
    safety_buffer = 200

    available_tokens = input_tokens + image_tokens + safety_buffer
    return available_tokens
