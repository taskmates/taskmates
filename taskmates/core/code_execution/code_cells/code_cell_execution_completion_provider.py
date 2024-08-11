import textwrap

import pytest

from taskmates.config.completion_context import CompletionContext
from taskmates.contexts import CONTEXTS, Contexts
from taskmates.core.code_execution.code_cells.code_cells_editor_completion import CodeCellsEditorCompletion
from taskmates.core.code_execution.code_cells.execute_markdown_on_local_kernel import \
    execute_markdown_on_local_kernel
from taskmates.core.completion_provider import CompletionProvider
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.types import Chat


class CodeCellExecutionCompletionProvider(CompletionProvider):
    def stop(self):
        raise NotImplementedError("Not implemented")

    def can_complete(self, chat):
        is_jupyter_enabled = chat.get("metadata", {}).get("jupyter_enabled", True)
        last_message = chat['messages'][-1]
        code_cells = last_message.get("code_cells", [])
        return is_jupyter_enabled and len(code_cells) > 0

    async def perform_completion(self, chat: Chat, contexts: Contexts, signals: Signals):
        completion_context: CompletionContext = contexts["completion_context"]
        markdown_path = completion_context["markdown_path"]
        cwd = completion_context["cwd"]
        env = completion_context["env"]

        messages = chat.get("messages", [])

        editor_completion = CodeCellsEditorCompletion(project_dir=cwd,
                                                      chat_file=markdown_path,
                                                      signals=signals)

        async def on_code_cell_chunk(code_cell_chunk):
            await editor_completion.process_code_cell_output(code_cell_chunk)

        with signals.response.code_cell_output.connected_to(on_code_cell_chunk):
            # TODO pass env here
            await execute_markdown_on_local_kernel(content=messages[-1]["content"],
                                                   markdown_path=markdown_path,
                                                   cwd=cwd,
                                                   env=env)

        await editor_completion.process_code_cells_completed()


@pytest.mark.asyncio
async def test_markdown_code_cells_assistance_streaming(tmp_path):
    signals = SIGNALS.get()
    code_cell_chunks = []
    markdown_chunks = []

    async def capture_code_cell_chunk(chunk):
        code_cell_chunks.append(chunk)

    async def capture_completion_chunk(chunk):
        markdown_chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_code_cell_chunk)
    signals.response.response.connect(capture_completion_chunk)

    chat: Chat = {
        "metadata": {},
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

    assistance = CodeCellExecutionCompletionProvider()
    await assistance.perform_completion(chat, CONTEXTS.get(), signals)

    assert "".join(markdown_chunks) == ('###### Cell Output: stdout [cell_0]\n'
                                        '\n'
                                        '<pre>\n'
                                        'Hello\n'
                                        'Beautiful\n'
                                        '</pre>\n'
                                        '\n'
                                        '###### Cell Output: stdout [cell_1]\n'
                                        '\n'
                                        '<pre>\n'
                                        'World\n'
                                        '</pre>\n'
                                        '\n')
