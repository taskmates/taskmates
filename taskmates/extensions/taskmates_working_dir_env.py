import os

from wrapt import wrap_function_wrapper

from taskmates.context_builders.api_context_builder import ApiContextBuilder
from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.sdk import TaskmatesExtension


class TaskmatesWorkingDirEnv(TaskmatesExtension):
    # outputs: completion_context.cwd

    def wraper(self, wrapped, instance, args, kwargs):
        contexts = wrapped(*args, **kwargs)
        working_dir = os.environ.get('TASKMATES_WORKING_DIR')

        if working_dir:
            contexts["completion_context"]["cwd"] = working_dir

        return contexts

    def initialize(self):
        wrap_function_wrapper(CliContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(ApiContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(SdkContextBuilder, 'build', self.wraper)
        wrap_function_wrapper(TestContextBuilder, 'build', self.wraper)
