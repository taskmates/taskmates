import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.core.execution_context import EXECUTION_CONTEXT, merge_jobs, ExecutionContext
from taskmates.core.daemons.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.daemons.return_value import ReturnValue
from taskmates.core.daemons.interrupt_request_mediator import InterruptRequestMediator
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.runner.contexts.contexts import Contexts


class ApiComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, ExecutionContext] | list[ExecutionContext] = None,
                 ):
        root_jobs = {
            # TODO: job state
            "interrupt_request_mediator": InterruptRequestMediator(),
            "interrupted_or_killed": InterruptedOrKilled(),
            # TODO: job output
            "return_value": ReturnValue(),
        }
        super().__init__(contexts=contexts, jobs=merge_jobs(jobs, root_jobs))

    @typechecked
    async def run(self, payload):
        signals = EXECUTION_CONTEXT.get()
        contexts = EXECUTION_CONTEXT.get().contexts
        try:
            await signals.artifact.artifact.send_async(
                {"name": "websockets_api_payload.json", "content": payload})

            markdown_chat = payload["markdown_chat"]
            return await MarkdownComplete(contexts=contexts).run(markdown_chat=markdown_chat)

        # TODO: remove after we properly tested client disconnect
        except asyncio.CancelledError:
            logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
            await signals.control.kill.send_async({})
        except Exception as e:
            await signals.outputs.error.send_async(e)
        finally:
            logger.info("DONE Closing websocket connection")
