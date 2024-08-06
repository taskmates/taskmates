def get_tool_contents(message):
    if message["role"] == "tool":
        return [{
            "type": "tool_result",
            "tool_use_id": message["tool_call_id"],
            "content": message["content"]
        }]
    else:
        return []
