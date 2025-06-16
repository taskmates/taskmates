from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.get_model_client import get_model_client
from taskmates.core.markdown_chat.metadata.get_model_conf import get_model_conf
from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.api_request import api_request
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.prepare_request_payload import \
    prepare_request_payload
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_markdown_appender import \
    LlmCompletionMarkdownAppender
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.llm_completion_signals import LlmCompletionSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import Chat
from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.get_model_client import get_model_client
from taskmates.core.markdown_chat.metadata.get_model_conf import get_model_conf
from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.api_request import api_request
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.prepare_request_payload import \
    prepare_request_payload
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_markdown_appender import \
    LlmCompletionMarkdownAppender
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.llm_completion_signals import LlmCompletionSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import Chat


@typechecked
class LlmCompletionProvider(CompletionProvider):
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
            chat_completion_signals: LlmCompletionSignals,
            code_cell_output_signals: CodeCellOutputSignals,
            status_signals: StatusSignals,
    ):
        contexts = RUN.get().context

        last_tool_call_id = 0
        for m in chat['messages']:
            if m.get('tool_calls'):
                last_tool_call_id = int(m.get('tool_calls')[-1].get('id'))

        chat_completion_markdown_appender = LlmCompletionMarkdownAppender(
            chat["messages"][-1]["recipient"],
            last_tool_call_id,
            self.has_truncated_code_cell(chat),
            markdown_completion_signals
        )

        async def restream_completion_chunk(chat_completion_chunk):
            await chat_completion_markdown_appender.process_chat_completion_chunk(chat_completion_chunk)

        with chat_completion_signals.chat_completion.connected_to(restream_completion_chunk):

            taskmates_dirs = contexts["runner_config"]["taskmates_dirs"]

            model_alias = contexts["run_opts"]["model"]
            model_conf = get_model_conf(model_alias=model_alias,
                                        messages=chat["messages"],
                                        taskmates_dirs=taskmates_dirs)

            model_conf.update({
                "temperature": 0.2,
                "stop": ["\n######"],
            })

            model_conf["stop"].extend(self.get_usernames_stop_sequences(chat))

            request_payload = prepare_request_payload(chat, model_conf)

            client = get_model_client(model_spec=model_conf)

            # # TODO: this doesn't look right
            # # Ensure 'model' is always present for downstream logic
            # if "model" not in request_payload:
            #     if model_conf.get("model_name") == "fixture":
            #         request_payload["model"] = "fixture"
            #     elif "model_name" in model_conf:
            #         request_payload["model"] = model_conf["model_name"]
            #     elif isinstance(model_alias, str):
            #         request_payload["model"] = model_alias
            #     else:
            #         request_payload["model"] = "unknown"

            return await api_request(client,
                                     request_payload,
                                     control_signals,
                                     status_signals,
                                     chat_completion_signals)

    def get_usernames_stop_sequences(self, chat):
        user_participants = ["user"]
        for name, config in chat["participants"].items():
            if config["role"] == "user" and name not in user_participants:
                user_participants.append(name)
        username_stop_sequences = [f"\n**{u}>** " for u in user_participants]
        return username_stop_sequences
