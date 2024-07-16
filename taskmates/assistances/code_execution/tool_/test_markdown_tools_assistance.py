import pytest

from taskmates.assistances.code_execution.tool_.markdown_tools_assistance import MarkdownToolsAssistance


@pytest.mark.asyncio
async def test_can_complete():
    chat = {
        "messages": [{"tool_calls": [{"function": {"name": "test_function"}}]}]
    }
    assistance = MarkdownToolsAssistance()
    assert assistance.can_complete(chat) is True

    chat["messages"][-1]["tool_calls"] = []
    assert assistance.can_complete(chat) is False


# @pytest.mark.asyncio
# async def test_perform_completion(mocker):
#     chat = {
#         "messages": [{"tool_calls": [{"id": "test_id", "function": {"name": "test_function", "arguments": "{}"}}]}]
#     }
#     context = {"markdown_path": "test.md", "cwd": "/test"}
#     signals = MagicMock()
#     signals.output.response.send_async = AsyncMock()
#
#     mocked_execute_task = mocker.patch.object(MarkdownToolsAssistance, "execute_task", return_value="test_return")
#
#     assistance = MarkdownToolsAssistance()
#     await assistance.perform_completion(context, chat, signals)
#
#     signals.output.response.send_async.assert_called_with("test_return")
#     mocked_execute_task.assert_called_with(context,
#                                            mocker.ANY,
#                                            # ToolCall.from_dict(chat["messages"][-1]["tool_calls"][0]),
#                                            signals)
#
#
# @pytest.mark.asyncio
# async def test_execute_task(mocker):
#     context = {"markdown_path": "test.md", "cwd": "/test"}
#     tool_call_dict = {"id": "test_id", "function": {"name": "test_function", "arguments": json.dumps({"arg1": "value1"})}}
#     tool_call = ToolCall.from_dict(tool_call_dict)
#
#
#     mocked_function_registry = mocker.patch(
#         "taskmates.tools.function_registry")
#     mocked_function_registry.__getitem__.return_value.return_value = "test_return"
#
#     return_value = await MarkdownToolsAssistance.execute_task(context, tool_call, None)
#
#     assert return_value == "test_return"
#     mocked_function_registry.__getitem__.assert_called_with("test_function")
#     mocked_function_registry.__getitem__.return_value.assert_called_with(arg1="value1")
