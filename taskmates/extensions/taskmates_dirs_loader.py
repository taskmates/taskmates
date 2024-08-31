from pathlib import Path

from wrapt import wrap_function_wrapper

from taskmates.context_builders.api_context_builder import ApiContextBuilder
from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.contexts import default_taskmates_dirs
from taskmates.sdk import TaskmatesExtension


class TaskmatesDirsLoader(TaskmatesExtension):
    # needs: completion_context.cwd

    def wraper(self, wrapped, instance, args, kwargs):
        contexts = wrapped(*args, **kwargs)

        local_taskmates_dir = str(Path(contexts["completion_context"]["cwd"]) / ".taskmates")
        overridden_taskmates_dirs = contexts["client_config"].get("taskmates_dirs", None)
        effective_taskmates_dirs = overridden_taskmates_dirs or [local_taskmates_dir, *default_taskmates_dirs]
        contexts["client_config"]["taskmates_dirs"] = effective_taskmates_dirs

        return contexts

    def initialize(self):
        wrap_function_wrapper(CliContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(ApiContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(SdkContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(TestContextBuilder, 'build', self.wraper)
