from pathlib import Path

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.runner.contexts.runner_context import default_taskmates_dirs
from taskmates.sdk.experimental.weave_interface_method import weave_interface_method
from taskmates.sdk import TaskmatesExtension


class TaskmatesDirsLoader(TaskmatesExtension):
    # needs: runner_environment.cwd

    def handle(self, wrapped, instance, args, kwargs):
        contexts = wrapped(*args, **kwargs)

        local_taskmates_dir = str(Path(contexts["runner_environment"]["cwd"]) / ".taskmates")
        overridden_taskmates_dirs = contexts["runner_config"].get("taskmates_dirs", None)
        effective_taskmates_dirs = overridden_taskmates_dirs or [local_taskmates_dir, *default_taskmates_dirs]
        contexts["runner_config"]["taskmates_dirs"] = effective_taskmates_dirs

        return contexts

    def initialize(self):
        cls = ContextBuilder
        function_name = 'build'
        handler = self.handle

        weave_interface_method(cls, function_name, handler)
