import json

from typeguard import typechecked

from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.load_model_config import load_model_config
from taskmates.contexts import Contexts
from taskmates.core.chat_completion.chat_completion_editor_completion import ChatCompletionEditorCompletion
from taskmates.core.completion_provider import CompletionProvider
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.formats.markdown.metadata.get_model_conf import get_model_conf
from taskmates.function_registry import function_registry
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.openai_.inference.api_request import api_request
from taskmates.lib.tool_schemas_.tool_schema import tool_schema
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class ChatCompletionProvider(CompletionProvider):
    def __init__(self, completion_opts: CompletionOpts):
        self.completion_opts = completion_opts

    def stop(self):
        raise NotImplementedError("Not implemented")

    def can_complete(self, chat):
        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(self, chat: Chat, contexts: Contexts, signals: Signals):
        model_alias = self.completion_opts["model"]

        chat_completion_editor_completion = ChatCompletionEditorCompletion(chat, signals)

        async def restream_completion_chunk(chat_completion_chunk):
            choice = chat_completion_chunk.model_dump()['choices'][0]
            await chat_completion_editor_completion.process_chat_completion_chunk(choice)

        with signals.response.chat_completion.connected_to(restream_completion_chunk):
            taskmates_dirs = self.completion_opts["taskmates_dirs"]
            model_conf = get_model_conf(model_alias=model_alias, messages=chat["messages"], taskmates_dirs=taskmates_dirs)
            tools = list(map(function_registry.__getitem__, chat["available_tools"]))
            tools_schemas = [tool_schema(f) for f in tools]

            messages = [{key: value for key, value in m.items()
                         if key not in ("recipient", "recipient_role", "code_cells")}
                        for m in chat["messages"]]

            for message in messages:
                tool_calls = message.get("tool_calls", [])
                for tool_call in tool_calls:
                    tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"],
                                                                    ensure_ascii=False)

            user_participants = ["user"]
            for name, config in chat["participants"].items():
                if config["role"] == "user" and name not in user_participants:
                    user_participants.append(name)

            model_conf.setdefault("stop", []).extend([f"\n**{u}>** " for u in user_participants])

            # TODO: This is currently not supported by Claude + Tools
            # recipient = chat['messages'][-1]['recipient_role']
            # assistant_prompt = f"**{recipient}>**"
            # messages.append({"content": assistant_prompt, "role": "assistant"})

            # TODO
            tool_choice = NOT_SET

            model_params = dict(
                **({"tools": tools_schemas} if tools else {}),
                **({"tool_choice": tool_choice} if tool_choice is not None else {})
            )

            await signals.output.artifact.send_async({"name": "parsed_chat.json", "content": chat})

            client = get_model_client(model_alias, taskmates_dirs)
            return await api_request(client, messages, model_conf, model_params, signals)
