import functools

from taskmates.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.workflow_engine.run import RUN, Run
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class MarkdownChatDaemon(CompositeContextManager):
    async def process_chunk(self, markdown: str, format: str, run: Run):
        run.state["markdown_chat"].append_to_format(format, markdown)

    def __enter__(self):
        run = RUN.get()
        connections = []

        incoming_markdown_chat = run.objective.key['inputs'].get("markdown_chat")
        if incoming_markdown_chat is not None:
            run.state["markdown_chat"].append_to_format("full", incoming_markdown_chat)

        input_streams = run.signals["input_streams"]
        execution_environment = run.signals["execution_environment"]
        markdown_completion = run.signals["markdown_completion"]

        connections.extend([
            input_streams.history.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            input_streams.incoming_message.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            input_streams.formatting.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            markdown_completion.formatting.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            markdown_completion.response.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            markdown_completion.responder.connected_to(
                functools.partial(self.process_chunk, format="full", run=run)),
            execution_environment.error.connected_to(
                functools.partial(self.process_chunk, format="full", run=run))
        ])
        connections.extend([
            markdown_completion.responder.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run)),
            markdown_completion.response.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run)),
            execution_environment.error.connected_to(
                functools.partial(self.process_chunk, format="completion", run=run))
        ])
        connections.append(markdown_completion.response.connected_to(
            functools.partial(self.process_chunk, format="text", run=run)))

        self.exit_stack.enter_context(stacked_contexts(connections))
