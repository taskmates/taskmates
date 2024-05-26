from enum import Enum

class Endpoint(Enum):
    COMPLETIONS = "/v1/completions"
    EDITS = "/v1/edits"
    CHAT_COMPLETIONS = "/v1/chat/completions"
    TASKMATES_COMPLETIONS = "/v1/taskmates/completions"
    TASKMATES_TOOLS = "/v1/taskmates/tools"
    ECHO = "/echo"

    @property
    def path(self):
        return self.value
