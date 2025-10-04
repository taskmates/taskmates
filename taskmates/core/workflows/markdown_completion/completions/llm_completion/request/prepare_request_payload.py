import json

from typeguard import typechecked

from taskmates.core.tools_registry import tools_registry
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.configure_vendor_specifics import \
    configure_vendor_specifics
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.types import ChatCompletionRequest


@typechecked
def prepare_request_payload(chat: ChatCompletionRequest, model_conf: dict, client=None):
    tools = list(map(tools_registry.__getitem__, chat["available_tools"]))

    # filter out metadata
    messages = [{key: value for key, value in m.items()
                 if key not in ("recipient", "recipient_role", "code_cells")}
                for m in chat["messages"]]

    # convert "arguments" to str
    for message in messages:
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"],
                                                            ensure_ascii=False)

    # TODO: This is currently not supported by Claude + Tools
    # recipient = chat['messages'][-1]['recipient_role']
    # assistant_prompt = f"**{recipient}>**"
    # messages.append({"content": assistant_prompt, "role": "assistant"})
    # TODO
    tool_choice = NOT_SET
    model_params = dict(
        **({"tools": tools} if tools else {}),
        **({"tool_choice": tool_choice} if tool_choice is not None else {})
    )
    # Clean up empty tool parameters
    if model_params.get("tool_choice", None) is NOT_SET:
        del model_params["tool_choice"]
    if "tools" in model_params and not model_params["tools"]:
        del model_params["tools"]
    request_payload = dict(messages=messages, **model_conf, **model_params)

    # Apply vendor-specific configurations if client is provided
    if client is not None:
        messages, tools = configure_vendor_specifics(client, messages, tools)
        request_payload['messages'] = messages
        if tools:
            request_payload['tools'] = tools
        elif 'tools' in request_payload:
            del request_payload['tools']

    return request_payload
