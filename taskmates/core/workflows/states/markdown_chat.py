from typing import Dict


class MarkdownChat:
    def __init__(self, initial=""):
        super().__init__()
        self.outputs = {
            "full": initial,
            "completion": "",
            "text": ""
        }

    def get(self) -> Dict[str, str]:
        return self.outputs

    def append_to_format(self, format: str, content: str) -> None:
        self.outputs[format] += content
