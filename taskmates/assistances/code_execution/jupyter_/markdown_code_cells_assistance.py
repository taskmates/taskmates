import textwrap

from taskmates.assistances.code_execution.jupyter_.execute_markdown_on_local_kernel import \
    execute_markdown_on_local_kernel
from taskmates.assistances.completion_assistance import CompletionAssistance
from taskmates.assistances.code_execution.jupyter_.code_cells_editor_completion import CodeCellsEditorCompletion


class MarkdownCodeCellsAssistance(CompletionAssistance):
    def stop(self):
        raise NotImplementedError("Not implemented")

    def can_complete(self, chat):
        is_jupyter_enabled = chat.get("metadata", {}).get("jupyter", True)
        last_message = chat.get("last_message", {})
        code_cells = last_message.get("code_cells", [])
        return is_jupyter_enabled and len(code_cells) > 0

    async def perform_completion(self, context, chat, signals):
        markdown_path = context["markdown_path"]
        messages = chat.get("messages", [])
        cwd = context.get("cwd")

        editor_completion = CodeCellsEditorCompletion(project_dir=cwd, chat_file=markdown_path,
                                                      signals=signals)

        async def on_code_cell_chunk(code_cell_chunk):
            await editor_completion.process_code_cell_output(code_cell_chunk)

        with signals.code_cell_output.connected_to(on_code_cell_chunk):
            await execute_markdown_on_local_kernel(content=messages[-1]["content"],
                                                   path=markdown_path,
                                                   cwd=cwd)

        await editor_completion.process_code_cells_completed()


import pytest
from taskmates.signals import SIGNALS


@pytest.mark.asyncio
async def test_markdown_code_cells_assistance_streaming(tmp_path):
    signals = SIGNALS.get()
    code_cell_chunks = []
    markdown_chunks = []

    async def capture_code_cell_chunk(chunk):
        code_cell_chunks.append(chunk)

    async def capture_completion_chunk(chunk):
        markdown_chunks.append(chunk)

    signals.code_cell_output.connect(capture_code_cell_chunk)
    signals.response.connect(capture_completion_chunk)

    chat = {
        "metadata": {"jupyter": True},
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

    context = {"markdown_path": str(tmp_path), "cwd": str(tmp_path)}

    assistance = MarkdownCodeCellsAssistance()
    await assistance.perform_completion(context, chat, signals)

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
