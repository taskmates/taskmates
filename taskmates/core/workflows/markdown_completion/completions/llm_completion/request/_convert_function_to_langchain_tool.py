from typing import Callable

from langchain_core.tools import BaseTool, StructuredTool


def _convert_function_to_langchain_tool(func: Callable) -> BaseTool:
    """Convert a raw function to a LangChain tool using StructuredTool.from_function."""
    if isinstance(func, StructuredTool):
        return func
    return StructuredTool.from_function(func=func)
