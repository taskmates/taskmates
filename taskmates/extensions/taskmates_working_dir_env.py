import os

from wrapt import wrap_function_wrapper

from taskmates.context_builders.context_builder import ContextBuilder
from taskmates.sdk import TaskmatesExtension
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


class TaskmatesWorkingDirEnv(TaskmatesExtension):
    # outputs: completion_context.cwd

    def wraper(self, wrapped, instance, args, kwargs):
        contexts = wrapped(*args, **kwargs)
        working_dir = os.environ.get('TASKMATES_WORKING_DIR')

        if working_dir:
            contexts["completion_context"]["cwd"] = working_dir

        return contexts

    def initialize(self):
        SubclassExtensionPoints.subscribe(ContextBuilder,
                                          lambda subclass: wrap_function_wrapper(subclass, 'build', self.wraper))
