from pathlib import Path

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.runner.contexts.contexts import default_taskmates_dirs
from taskmates.sdk.experimental.weave_interface_method import weave_interface_method
from taskmates.sdk import TaskmatesExtension


class TaskmatesDirsLoader(TaskmatesExtension):
    # needs: completion_context.cwd

    def handle(self, wrapped, instance, args, kwargs):
        contexts = wrapped(*args, **kwargs)

        local_taskmates_dir = str(Path(contexts["completion_context"]["cwd"]) / ".taskmates")
        overridden_taskmates_dirs = contexts["client_config"].get("taskmates_dirs", None)
        effective_taskmates_dirs = overridden_taskmates_dirs or [local_taskmates_dir, *default_taskmates_dirs]
        contexts["client_config"]["taskmates_dirs"] = effective_taskmates_dirs

        return contexts

    def initialize(self):
        cls = ContextBuilder
        function_name = 'build'
        handler = self.handle

        weave_interface_method(cls, function_name, handler)
