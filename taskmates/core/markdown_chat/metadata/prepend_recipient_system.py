import datetime
from pathlib import Path

import jinja2
from jinja2 import Environment
from typeguard import typechecked

from taskmates.core.markdown_chat.participants.compute_introduction_message import compute_introduction_message
from taskmates.core.markdown_chat.participants.format_username_prompt import format_username_prompt


@typechecked
def prepend_recipient_system(taskmates_dirs: list[str | Path],
                             participants_configs: dict,
                             recipient: str,
                             recipient_config: dict,
                             messages: list,
                             inputs: dict | None):
    if inputs is None:
        inputs = {}
    recipient_system_parts = []
    if recipient_config.get("system", None):
        recipient_system_parts.append(recipient_config.get("system").rstrip("\n") + "\n")
    introduction_message = compute_introduction_message(participants_configs, taskmates_dirs)
    if introduction_message:
        recipient_system_parts.append(introduction_message)
    if recipient != "assistant":
        recipient_system_parts.append(format_username_prompt(recipient) + "\n")
    recipient_system = "\n".join(recipient_system_parts)

    # setup system
    if recipient_system != '':
        if messages[0]["role"] == "system":
            messages = [{"role": "system", "content": recipient_system}, *messages[1:]]
        else:
            messages = [{"role": "system", "content": recipient_system}, *messages]

    if messages[0]["role"] == "system":
        messages[0]["content"] = render_template(messages[0]["content"], inputs)

    return messages


def render_template(template, inputs):
    env = create_env()
    return env.from_string(template).render(inputs)


def create_env():
    env = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined)
    env.globals['datetime'] = datetime
    return env
