import copy
import json
import textwrap

from typeguard import typechecked

from taskmates.lib.openai_.count_tokens import count_tokens

# https://platform.openai.com/docs/models
CONTEXT_WINDOWS = {
    "gpt-4o": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-3.5-turbo-instruct": 4096,
    "text-davinci-003": 4096,
    "text-davinci-002": 4096,
    "code-davinci-002": 8001,
    # groq
    "llama3-70b-8192": 8192,
    "mixtral-8x7b-32768": 32768,
    # anthropic
    "claude-3-haiku-20240307": 4096,
    "claude-3-opus-20240229": 4096,
    "claude-3-sonnet-20240229": 4096,
    "claude-3-5-sonnet-20240620": 4096,
    "echo": 4096,
    "quote": 4096,
    # ollama
    "codeqwen": 64000,
}


@typechecked
def calculate_max_tokens(messages: list, model_name: str):
    images = 0
    if "claude" in model_name:
        return 4096
    if "llama" in model_name:
        return 4096
    else:
        approximate_payload = copy.deepcopy(messages)
        for message in approximate_payload:
            if isinstance(message.get("content", None), list):
                for part in message.get("content", []):
                    if part["type"] != "text":
                        del part["image_url"]
                        images += 1

        available_tokens = CONTEXT_WINDOWS[model_name] - count_tokens(
            json.dumps(approximate_payload, ensure_ascii=False)) - (images * 100)
        return min(available_tokens - 200, 4096)


@typechecked
def get_model_conf(model_name: str, messages: list):
    max_tokens = calculate_max_tokens(messages, model_name)

    model_conf = {
        **{"model": model_name,
           "max_tokens": max_tokens,
           "temperature": 0.2,
           "stop": ["\n######"],
           "stream": True}
    }

    return model_conf


def test_handling_wrapped_json_in_payload_role():
    message = '''
    ```json
    {
        "key": "value"
    }
    ```
    '''
    payload = {
        "model": "gpt-4",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": textwrap.dedent(message)
            }
        ]
    }
    updated_payload = get_model_conf("gpt-4", payload["messages"])
    assert updated_payload == {'max_tokens': 4096,
                               'model': 'gpt-4',
                               'stop': ['\n######'],
                               'stream': True,
                               'temperature': 0.2}


def test_handling_wrapped_json_and_extra_text_in_payload_role():
    payload_message = '''
    ```json
    {
        "key": "value"
    }
    ```
    Some extra text
    '''
    payload = {
        "model": "gpt-4",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "payload",
                "content": textwrap.dedent(payload_message)
            }
        ]
    }
    updated_payload = get_model_conf("gpt-4", payload["messages"])
    assert updated_payload == {'max_tokens': 4096,
                               'model': 'gpt-4',
                               'stop': ['\n######'],
                               'stream': True,
                               'temperature': 0.2}
