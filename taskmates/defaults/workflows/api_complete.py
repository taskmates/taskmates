import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.core.execution_context import EXECUTION_CONTEXT


class ApiComplete(TaskmatesWorkflow):
    @typechecked
    async def run(self, payload):
        signals = EXECUTION_CONTEXT.get()
        contexts = EXECUTION_CONTEXT.get().contexts
        try:
            await signals.artifact.artifact.send_async(
                {"name": "websockets_api_payload.json", "content": payload})

            markdown_chat = payload["markdown_chat"]
            return await MarkdownComplete(contexts=contexts).run(current_markdown=markdown_chat)

        # TODO: remove after we properly tested client disconnect
        except asyncio.CancelledError:
            logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
            await signals.control.kill.send_async({})
        except Exception as e:
            await signals.outputs.error.send_async(e)
        finally:
            logger.info("DONE Closing websocket connection")
