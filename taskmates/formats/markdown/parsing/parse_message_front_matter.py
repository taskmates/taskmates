import json
import yaml

from taskmates.formats.openai.get_text_content import get_text_content


def parse_message_front_matter(message):
    content = get_text_content(message)

    if content.startswith("```json"):
        # Find the closing backticks
        end = content.find("```", 7)
        if end == -1:
            raise ValueError("Invalid JSON front matter")

        content = content[7:end].strip()

        try:
            message_payload = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                content = content[start:end]
                message_payload = json.loads(content)
            else:
                message_payload = {}
        return message_payload
    elif content.startswith("```yaml"):
        # Find the closing backticks
        end = content.find("```", 7)
        if end == -1:
            raise ValueError("Invalid YAML front matter")

        content = content[7:end].strip()

        try:
            message_payload = yaml.safe_load(content)
        except yaml.YAMLError:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                content = content[start:end]
                message_payload = yaml.safe_load(content)
            else:
                message_payload = {}
        return message_payload
    else:
        return {}
