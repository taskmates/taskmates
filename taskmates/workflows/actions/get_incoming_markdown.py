from taskmates.workflow_engine.environment import environment
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.run import RUN
from taskmates.workflows.actions.read_history import read_history
from taskmates.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.workflows.signals.processors.incoming_messages_formatting_processor import \
    IncomingMessagesFormattingProcessor
from taskmates.workflows.states.markdown_chat import MarkdownChat


@fulfills(outcome="incoming_markdown")
@environment(
    daemons_fn=lambda: [MarkdownChatDaemon(),
                        IncomingMessagesFormattingProcessor()],
    state_fn=lambda: {"markdown_chat": MarkdownChat()}
)
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
