import textwrap

import pytest
from typeguard import typechecked

from taskmates.core.chat.openai.get_text_content import get_text_content
from taskmates.core.workflow_engine.transactions.transaction import Transaction, TRANSACTION
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execute_markdown_on_local_kernel import \
    execute_markdown_on_local_kernel
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.response.code_cell_execution_appender import \
    CodeCellExecutionAppender
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import CompletionRequest, RunnerEnvironment


@typechecked
class CodeCellExecutionCompletionProvider(CompletionProvider):
    def __init__(self):
        self.execution_environment_signals = ExecutionEnvironmentSignals(name="code_cell_output")

    def can_complete(self, chat: CompletionRequest):
        messages = chat["messages"]

        if has_truncated_code_cell(messages):
            return False

        code_cells = messages[-1].get("code_cells", [])
        return len(code_cells) > 0

    async def perform_completion(
            self,
            chat: CompletionRequest,
            control_signals: ControlSignals,
            execution_environment_signals: ExecutionEnvironmentSignals,
            status_signals: StatusSignals
    ):
        messages = chat.get("messages", [])
        contexts = TRANSACTION.get().context

        runner_environment: RunnerEnvironment = contexts["runner_environment"]
        markdown_path = runner_environment["markdown_path"]
        cwd = runner_environment["cwd"]
        env = runner_environment["env"]


        editor_completion = CodeCellExecutionAppender(project_dir=cwd,
                                                      chat_file=markdown_path,
                                                      execution_environment_signals=execution_environment_signals)

        async def on_code_cell_chunk(sender, value):
            await editor_completion.process_code_cell_output(value)

        with self.execution_environment_signals.response.connected_to(on_code_cell_chunk, sender="code_cell_output"):
            text_content = get_text_content(messages[-1])
            # TODO pass env here
            await execute_markdown_on_local_kernel(
                control=control_signals,
                status=status_signals,
                execution_environment_signals=self.execution_environment_signals,
                content=text_content,
                markdown_path=markdown_path,
                cwd=cwd,
                env=env)

        await editor_completion.process_code_cells_completed()


@pytest.mark.asyncio
async def test_markdown_code_cells_assistance_streaming(tmp_path, transaction: Transaction):
    markdown_chunks = []

    async def capture_completion_chunk(sender, value):
        markdown_chunks.append(value)

    async def capture_error(error):
        raise error

    chat: CompletionRequest = {
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

    control_signals = ControlSignals(name="test-control_signals =")
    status_signals = StatusSignals(name="test-status_signals =")
    execution_environment_signals = ExecutionEnvironmentSignals(name="test-execution_environment_signals")
    execution_environment_signals.response.connect(capture_completion_chunk)
    execution_environment_signals.error.connect(capture_error)
    assistance = CodeCellExecutionCompletionProvider()
    async with transaction.async_transaction_context():
        await assistance.perform_completion(
            chat,
            control_signals,
            execution_environment_signals,
            status_signals,
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
