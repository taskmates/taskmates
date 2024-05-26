import pytest

from taskmates.assistances.code_execution.jupyter_.markdown_code_cells_assistance import MarkdownCodeCellsAssistance


@pytest.mark.asyncio
async def test_can_complete():
    chat = {
        "metadata": {"jupyter": True},
        "last_message": {"code_cells": [{"source": "print('test')"}]}
    }
    assistance = MarkdownCodeCellsAssistance()
    assert assistance.can_complete(chat) == True

    chat["metadata"]["jupyter"] = False
    assert assistance.can_complete(chat) == False

    chat["last_message"]["code_cells"] = []
    assert assistance.can_complete(chat) == False


# @pytest.mark.asyncio
# async def test_perform_completion(mocker):
#     chat = {
#         "messages": [{"content": "```python\nprint('test')\n```"}]
#     }
#     context = {"markdown_path": "test.md", "cwd": "/test"}
#     signals = MagicMock()
#     signals.response.send_async = AsyncMock()
#
#     mocked_execute_markdown = mocker.patch(
#         "taskmates.assistances.markdown.markdown_code_cells_assistance.execute_markdown",
#         return_value=[{"source": "print('test')", "outputs": []}])
#
#     assistance = MarkdownCodeCellsAssistance()
#     await assistance.perform_completion(context, chat, signals)
#
#     signals.response.send_async.assert_called()
#     mocked_execute_markdown.assert_called_with(content=chat["messages"][-1]["content"],
#                                                path=context["markdown_path"],
#                                                cwd=context["cwd"])
