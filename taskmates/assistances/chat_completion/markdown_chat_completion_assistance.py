from typeguard import typechecked

from taskmates.assistances.chat_completion.chat_completion_editor_completion import ChatCompletionEditorCompletion
from taskmates.assistances.completion_assistance import CompletionAssistance
from taskmates.config import CompletionContext, CompletionOpts, COMPLETION_OPTS
from taskmates.formats.markdown.metadata.process_model_conf import process_model_conf
from taskmates.function_registry import function_registry
from taskmates.lib.logging_.file_logger import file_logger
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.openai_.inference.api_request import api_request
from taskmates.lib.tool_schemas_.tool_schema import tool_schema
from taskmates.signals import Signals
from taskmates.types import Chat


class MarkdownChatCompletionAssistance(CompletionAssistance):
    def stop(self):
        raise NotImplementedError("Not implemented")

    def can_complete(self, chat):
        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(self, context: CompletionContext, chat: Chat, signals: Signals):
        completion_opts: CompletionOpts = COMPLETION_OPTS.get()
        model = completion_opts["model"]

        chat_completion_editor_completion = ChatCompletionEditorCompletion(chat, signals)

        async def restream_completion_chunk(chat_completion_chunk):
            choice = chat_completion_chunk.model_dump()['choices'][0]
            await chat_completion_editor_completion.process_chat_completion_chunk(choice)

        with signals.chat_completion.connected_to(restream_completion_chunk):
            model_conf = process_model_conf(model_name=model, messages=chat["messages"])
            tools = list(map(function_registry.__getitem__, chat["available_tools"]))
            tools_schemas = [tool_schema(f) for f in tools]

            messages = [{"name": m.get("name"), "role": m["role"], "content": m["content"]} for m in chat["messages"]]

            # TODO
            tool_choice = NOT_SET
            model_params = dict(
                **({"tools": tools_schemas} if tools else {}),
                **({"tool_choice": tool_choice} if tool_choice is not None else {})
            )

            file_logger.debug(f"[api_request] chat.yaml", content=chat)
            file_logger.debug(f"[api_request] chat.json", content=chat)

            return await api_request(messages, model_conf, model_params)
