from typeguard import typechecked

from taskmates.core.actions.chat_completion.chat_completion_markdown_appender import ChatCompletionMarkdownAppender
from taskmates.core.actions.chat_completion.prepare_request_payload import prepare_request_payload
from taskmates.core.completion_provider import CompletionProvider
from taskmates.formats.markdown.metadata.get_model_client import get_model_client
from taskmates.formats.markdown.metadata.get_model_conf import get_model_conf
from taskmates.lib.openai_.inference.api_request import api_request
from taskmates.types import Chat
from taskmates.workflow_engine.run import RUN
from taskmates.workflows.signals.chat_completion_signals import ChatCompletionSignals
from taskmates.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.workflows.signals.status_signals import StatusSignals


@typechecked
class ChatCompletionProvider(CompletionProvider):
    def can_complete(self, chat):
        if self.has_truncated_code_cell(chat):
            return True

        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(
            self,
            chat: Chat,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            chat_completion_signals: ChatCompletionSignals,
            code_cell_output_signals: CodeCellOutputSignals,
            status_signals: StatusSignals
    ):
        contexts = RUN.get().context
        chat_completion_markdown_appender = ChatCompletionMarkdownAppender(
            chat,
            self.has_truncated_code_cell(chat),
            markdown_completion_signals
        )

        async def restream_completion_chunk(chat_completion_chunk):
            choice = chat_completion_chunk.model_dump()['choices'][0]
            await chat_completion_markdown_appender.process_chat_completion_chunk(choice)

        with chat_completion_signals.chat_completion.connected_to(restream_completion_chunk):
            taskmates_dirs = contexts["runner_config"]["taskmates_dirs"]
            model_alias = contexts["run_opts"]["model"]
            model_conf = get_model_conf(model_alias=model_alias,
                                        messages=chat["messages"],
                                        taskmates_dirs=taskmates_dirs)
            client = get_model_client(model_alias=model_alias,
                                      taskmates_dirs=taskmates_dirs)

            force_stream = bool(chat_completion_signals.chat_completion.receivers)

            request_payload = prepare_request_payload(chat, model_conf, force_stream)
            return await api_request(client, request_payload,
                                     control_signals,
                                     status_signals,
                                     chat_completion_signals)
