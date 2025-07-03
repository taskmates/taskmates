import textwrap

import pytest
from typeguard import typechecked

from taskmates.core.chat.openai.get_text_content import get_text_content
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.response.code_cell_execution_appender import CodeCellExecutionAppender
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execute_markdown_on_local_kernel import \
    execute_markdown_on_local_kernel
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.types import Chat, RunnerEnvironment
from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.signals.llm_completion_signals import LlmCompletionSignals
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals


@typechecked
class CodeCellExecutionCompletionProvider(CompletionProvider):
    def can_complete(self, chat):
        if self.has_truncated_code_cell(chat):
            return False

        is_jupyter_enabled = chat.get("run_opts", {}).get("jupyter_enabled", True)
        last_message = chat['messages'][-1]
        code_cells = last_message.get("code_cells", [])
        return is_jupyter_enabled and len(code_cells) > 0

    async def perform_completion(
            self,
            chat: Chat,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            chat_completion_signals: LlmCompletionSignals,
            code_cell_output_signals: CodeCellOutputSignals,
            status_signals: StatusSignals
    ):
        contexts = RUN.get().context

        runner_environment: RunnerEnvironment = contexts["runner_environment"]
        markdown_path = runner_environment["markdown_path"]
        cwd = runner_environment["cwd"]
        env = runner_environment["env"]

        messages = chat.get("messages", [])

        editor_completion = CodeCellExecutionAppender(project_dir=cwd,
                                                      chat_file=markdown_path,
                                                      markdown_completion_signals=markdown_completion_signals)

        async def on_code_cell_chunk(code_cell_chunk):
            await editor_completion.process_code_cell_output(code_cell_chunk)

        with code_cell_output_signals.code_cell_output.connected_to(on_code_cell_chunk):
            text_content = get_text_content(messages[-1])
            # TODO pass env here
            await execute_markdown_on_local_kernel(content=text_content,
                                                   markdown_path=markdown_path,
                                                   cwd=cwd,
                                                   env=env)

        await editor_completion.process_code_cells_completed()


@pytest.mark.asyncio
async def test_markdown_code_cells_assistance_streaming(tmp_path):
    code_cell_chunks = []
    markdown_chunks = []

    async def capture_code_cell_chunk(chunk):
        code_cell_chunks.append(chunk)

    async def capture_completion_chunk(chunk):
        markdown_chunks.append(chunk)

    async def capture_error(error):
        raise error

    chat: Chat = {
        "markdown_chat": "",
        "run_opts": {},
        "participants": {},
        "available_tools": [],
        "messages": [
            {
                "content": textwrap.dedent("""\
                    ```python .eval
                    import time
                    print("Hello")
                    time.sleep(2)
                    print("Beautiful")
                    ```

                    ```python .eval
                    print("World")
                    ```
                """)
            }
        ]
    }

    signals = RUN.get().signals
    execution_environment_signals = signals["execution_environment"]
    code_cell_output_signals = signals["code_cell_output"]
    markdown_completion_signals = signals["markdown_completion"]
    code_cell_output_signals.code_cell_output.connect(capture_code_cell_chunk)
    markdown_completion_signals.response.connect(capture_completion_chunk)
    execution_environment_signals.error.connect(capture_error)
    assistance = CodeCellExecutionCompletionProvider()
    await assistance.perform_completion(
        chat,
        signals["control"],
        markdown_completion_signals,
        signals["chat_completion"],
        code_cell_output_signals,
        signals["status"],
    )

    assert "".join(markdown_chunks) == ('###### Cell Output: stdout [cell_0]\n'
                                        '\n'
                                        '<pre>\n'
                                        'Hello\n'
                                        'Beautiful\n'
                                        '\n</pre>\n'
                                        '\n'
                                        '###### Cell Output: stdout [cell_1]\n'
                                        '\n'
                                        '<pre>\n'
                                        'World\n'
                                        '\n</pre>\n'
                                        '\n')
