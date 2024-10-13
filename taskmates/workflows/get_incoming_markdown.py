from taskmates.workflow_engine.run import RUN
from taskmates.workflows.read_history import read_history


async def get_incoming_markdown(history_path, incoming_messages) -> str:
    run = RUN.get()
    if history_path:
        history = read_history(history_path)
        if history:
            await run.signals["input_streams"].history.send_async(history)

    for incoming_message in incoming_messages:
        if incoming_message:
            await run.signals["input_streams"].incoming_message.send_async(incoming_message)
    markdown_chat = run.state["markdown_chat"].get()["full"]

    run.state["incoming_markdown"] = markdown_chat
    return markdown_chat
