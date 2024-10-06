import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.core.run import RUN, Run
from taskmates.core.merge_jobs import merge_jobs
from taskmates.core.daemons.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.daemons.return_value import ReturnValue
from taskmates.core.daemons.interrupt_request_mediator import InterruptRequestMediator
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.runner.contexts.contexts import Contexts


class ApiComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, Run] | list[Run] = None,
                 ):
        control_flow_jobs = {
            "interrupt_request_mediator": InterruptRequestMediator(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
        }
        super().__init__(contexts=contexts, jobs=merge_jobs(jobs, control_flow_jobs))

    @typechecked
    async def run(self, payload):
        signals = RUN.get()
        contexts = RUN.get().contexts
        try:
            await signals.output_streams.artifact.send_async(
                {"name": "websockets_api_payload.json", "content": payload})

            markdown_chat = payload["markdown_chat"]
            return await MarkdownComplete(contexts=contexts).run(markdown_chat=markdown_chat)

        # TODO: remove after we properly tested client disconnect
        except asyncio.CancelledError:
            logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
            await signals.control.kill.send_async({})
        except Exception as e:
            await signals.output_streams.error.send_async(e)
        finally:
            logger.info("DONE Closing websocket connection")
