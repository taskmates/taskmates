import functools
from typing import Dict

from taskmates.core.run import RUN, Run
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class MarkdownChat(Run):
    def __init__(self):
        super().__init__()
        self.markdown_chunks = []
        self.outputs = {"full": "",
                        "completion": "",
                        "text": ""}

    async def process_chunk(self, markdown, format):
        self.outputs[format] += markdown

    def __enter__(self):
        run = RUN.get()
        connections = []

        if run.inputs.get("markdown_chat") is not None:
            self.outputs["full"] += run.inputs.get("markdown_chat")

        connections.extend([
            run.input_streams.history.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.input_streams.incoming_message.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.input_streams.formatting.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.output_streams.formatting.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.output_streams.response.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.output_streams.responder.connected_to(
                functools.partial(self.process_chunk, format="full")),
            run.output_streams.error.connected_to(
                functools.partial(self.process_chunk, format="full"))
        ])
        connections.extend([
            run.output_streams.responder.connected_to(
                functools.partial(self.process_chunk, format="completion")),
            run.output_streams.response.connected_to(
                functools.partial(self.process_chunk, format="completion")),
            run.output_streams.error.connected_to(
                functools.partial(self.process_chunk, format="completion"))
        ])
        connections.append(run.output_streams.response.connected_to(
            functools.partial(self.process_chunk, format="text")))

        self.exit_stack.enter_context(stacked_contexts(connections))

    def get(self) -> Dict[str, str]:
        return self.outputs
