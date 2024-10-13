import functools

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.run import RUN, Run
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class MarkdownChatDaemon(Daemon):
    async def process_chunk(self, markdown: str, format: str, run: Run):
        run.state["markdown_chat"].append_to_format(format, markdown)

    def __enter__(self):
        run = RUN.get()
        connections = []

        incoming_markdown_chat = run.objective.inputs.get("markdown_chat")
        if incoming_markdown_chat is not None:
            run.state["markdown_chat"].append_to_format("full", incoming_markdown_chat)

        input_streams = run.signals["input_streams"]
        output_streams = run.signals["output_streams"]
        connections.extend([
            input_streams.history.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            input_streams.incoming_message.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            input_streams.formatting.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            output_streams.formatting.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            output_streams.response.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            output_streams.responder.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            output_streams.error.connected_to(
                functools.partial(self.process_chunk, format="full", run=run))
        ])
        connections.extend([
            output_streams.responder.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run)),
            output_streams.response.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run)),
            output_streams.error.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run))
        ])
        connections.append(output_streams.response.connected_to(
            functools.partial(self.process_chunk, format="text", run=run)))

        self.exit_stack.enter_context(stacked_contexts(connections))
