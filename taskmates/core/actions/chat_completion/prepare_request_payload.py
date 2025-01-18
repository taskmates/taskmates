import json
from random import random

from taskmates.core.tools_registry import tools_registry
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.tool_schemas_.tool_schema import tool_schema
from taskmates.types import Chat


def prepare_request_payload(chat: Chat, model_conf: dict, force_stream: bool):
    tools = list(map(tools_registry.__getitem__, chat["available_tools"]))
    tools_schemas = [tool_schema(f) for f in tools]
    messages = [{key: value for key, value in m.items()
                 if key not in ("recipient", "recipient_role", "code_cells")}
                for m in chat["messages"]]
    for message in messages:
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"],
                                                            ensure_ascii=False)
    user_participants = ["user"]
    for name, config in chat["participants"].items():
        if config["role"] == "user" and name not in user_participants:
            user_participants.append(name)
    if force_stream:
        model_conf.update({"stream": True})
    model_conf.setdefault("stop", []).extend([f"\n**{u}>** " for u in user_participants])
    # TODO: This is currently not supported by Claude + Tools
    # recipient = chat['messages'][-1]['recipient_role']
    # assistant_prompt = f"**{recipient}>**"
    # messages.append({"content": assistant_prompt, "role": "assistant"})
    # TODO
    tool_choice = NOT_SET
    model_params = dict(
        **({"tools": tools_schemas} if tools else {}),
        **({"tool_choice": tool_choice} if tool_choice is not None else {})
    )
    # Clean up empty tool parameters
    if model_params.get("tool_choice", None) is NOT_SET:
        del model_params["tool_choice"]
    if "tools" in model_params and not model_params["tools"]:
        del model_params["tools"]
    # Add random seed
    seed = int(random() * 1000000)
    request_payload = dict(messages=messages, **model_conf, **model_params, seed=seed)
    return request_payload
