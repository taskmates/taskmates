import json

from typeguard import typechecked

from taskmates.core.actions.chat_completion.chat_completion_editor_completion import ChatCompletionEditorCompletion
from taskmates.core.completion_provider import CompletionProvider
from taskmates.core.tools_registry import tools_registry
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.formats.markdown.metadata.get_model_conf import get_model_conf
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.openai_.inference.api_request import api_request
from taskmates.lib.tool_schemas_.tool_schema import tool_schema
from taskmates.types import Chat
from taskmates.workflow_engine.run import RUN
from taskmates.workflow_engine.run import Run


class ChatCompletionProvider(CompletionProvider):
    def can_complete(self, chat):
        if self.has_truncated_response(chat):
            return True

        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(self, chat: Chat):
        contexts = RUN.get().context
        run: Run = RUN.get()
        output_streams = run.signals["output_streams"]

        chat_completion_editor_completion = ChatCompletionEditorCompletion(chat, self.has_truncated_response(chat), run)

        async def restream_completion_chunk(chat_completion_chunk):
            choice = chat_completion_chunk.model_dump()['choices'][0]
            await chat_completion_editor_completion.process_chat_completion_chunk(choice)

        with output_streams.chat_completion.connected_to(restream_completion_chunk):
            taskmates_dirs = contexts["runner_config"]["taskmates_dirs"]
            model_alias = contexts["run_opts"]["model"]
            model_conf = get_model_conf(model_alias=model_alias,
                                        messages=chat["messages"],
                                        taskmates_dirs=taskmates_dirs)
            client = get_model_client(model_alias=model_alias,
                                      taskmates_dirs=taskmates_dirs)

            tools = list(map(tools_registry.__getitem__, chat["available_tools"]))
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

            await output_streams.artifact.send_async({"name": "parsed_chat.json", "content": chat})

            return await api_request(client, messages, model_conf, model_params, run)
