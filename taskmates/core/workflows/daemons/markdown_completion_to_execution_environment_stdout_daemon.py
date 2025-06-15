import functools

from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.run import RUN, Run


class MarkdownCompletionToExecutionEnvironmentStdoutDaemon(CompositeContextManager):
    async def process_stdout(self, message: str, run: Run):
        await run.signals["execution_environment"].stdout.send_async(message)

    def __enter__(self):
        run = RUN.get()
        connections = []

        markdown_completion = run.signals["markdown_completion"]

        # Connect standard output streams
        connections.extend([
            markdown_completion.formatting.connected_to(
                functools.partial(self.process_stdout, run=run)),
            markdown_completion.responder.connected_to(
                functools.partial(self.process_stdout, run=run)),
            markdown_completion.response.connected_to(
                functools.partial(self.process_stdout, run=run)),
            markdown_completion.next_responder.connected_to(
                functools.partial(self.process_stdout, run=run)),
        ])

        self.exit_stack.enter_context(stacked_contexts(connections))
