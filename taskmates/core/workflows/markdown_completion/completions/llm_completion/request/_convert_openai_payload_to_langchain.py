import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, ToolCall
from langchain_core.tools import BaseTool
from typeguard import typechecked

from taskmates.core.workflows.markdown_completion.completions.llm_completion.request._convert_function_to_langchain_tool import \
    _convert_function_to_langchain_tool


@typechecked
def _convert_openai_payload_to_langchain(payload: dict) -> tuple[list[BaseMessage], list[BaseTool]]:
    # Map OpenAI role strings to LangChain message classes
    role_map = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
        "tool": ToolMessage,
    }

    # Convert message list
    messages = []
    for msg in payload["messages"]:
        content = msg["content"] or ""

        raw_tool_calls = msg.get("tool_calls", [])
        tool_calls = []

        for tool_call in raw_tool_calls:
            id = tool_call["id"]
            type = tool_call["type"]
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            tool_calls.append(ToolCall(name=name, args=args, id=id, type=type))

        msg_args = dict(
            content=content,
            tool_calls=tool_calls
        )

        if "tool_call_id" in msg:
            msg_args["tool_call_id"] = msg.get("tool_call_id")

        message = role_map[msg["role"]](**msg_args)
        messages.append(message)

    # Convert raw functions to LangChain tools
    raw_tools = payload.get("tools", [])
    tools: list[BaseTool] = []
    for tool_func in raw_tools:
        if callable(tool_func):
            langchain_tool = _convert_function_to_langchain_tool(tool_func)
            tools.append(langchain_tool)

    return messages, tools
