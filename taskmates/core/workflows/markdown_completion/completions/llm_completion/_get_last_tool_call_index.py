def _get_last_tool_call_index(chat):
    last_tool_call_id = 0
    for m in chat['messages']:
        if m.get('tool_calls'):
            last_tool_call_id = int(m.get('tool_calls')[-1].get('id'))
    return last_tool_call_id
