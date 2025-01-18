from typeguard import typechecked

from taskmates.core.actions.chat_completion.chat_completion_markdown_appender import ChatCompletionMarkdownAppender
from taskmates.core.actions.chat_completion.prepare_request_payload import prepare_request_payload
from taskmates.core.completion_provider import CompletionProvider
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.formats.markdown.metadata.get_model_conf import get_model_conf
from taskmates.lib.openai_.inference.api_request import api_request
from taskmates.types import Chat
from taskmates.workflow_engine.run import RUN
from taskmates.workflow_engine.run import Run
from taskmates.workflows.signals.output_streams import OutputStreams


class ChatCompletionProvider(CompletionProvider):
    def can_complete(self, chat):
        if self.has_truncated_response(chat):
            return True

        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(self, chat: Chat):
        current_run: Run = RUN.get()
        contexts = current_run.context
        output_streams: OutputStreams = current_run.signals["output_streams"]

        chat_completion_markdown_appender = ChatCompletionMarkdownAppender(chat, self.has_truncated_response(chat),
                                                                           output_streams)

        async def restream_completion_chunk(chat_completion_chunk):
            choice = chat_completion_chunk.model_dump()['choices'][0]
            await chat_completion_markdown_appender.process_chat_completion_chunk(choice)

        with output_streams.chat_completion.connected_to(restream_completion_chunk):
            taskmates_dirs = contexts["runner_config"]["taskmates_dirs"]
            model_alias = contexts["run_opts"]["model"]
            model_conf = get_model_conf(model_alias=model_alias,
                                        messages=chat["messages"],
                                        taskmates_dirs=taskmates_dirs)
            client = get_model_client(model_alias=model_alias,
                                      taskmates_dirs=taskmates_dirs)

            force_stream = bool(output_streams.chat_completion.receivers)

            request_payload = prepare_request_payload(chat, model_conf, force_stream)
            await output_streams.artifact.send_async({"name": "request_payload.json", "content": request_payload})

            return await api_request(client, request_payload, current_run)
