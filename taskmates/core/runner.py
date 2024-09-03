import copy

from taskmates.lib.context_.temp_context import temp_context
from taskmates.runner.contexts.contexts import CONTEXTS, Contexts
from taskmates.core.workflow_registry import workflow_registry
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


class Runner:
    async def run(self, inputs: dict, contexts: Contexts):
        TASKMATES_RUNTIME.get().initialize()

        with temp_context(CONTEXTS, copy.deepcopy(contexts)):
            workflow_name = contexts["completion_opts"]["workflow"]
            workflow = workflow_registry[workflow_name]()
            await workflow.run(**inputs)
