import os

from typing_extensions import override

from taskmates.contexts import Contexts
from taskmates.sdk import TaskmatesExtension


class TaskmatesWorkingDirEnv(TaskmatesExtension):
    @override
    def after_build_contexts(self, contexts: Contexts):
        working_dir = os.environ.get('TASKMATES_WORKING_DIR')

        if working_dir:
            contexts["completion_context"]["cwd"] = working_dir
