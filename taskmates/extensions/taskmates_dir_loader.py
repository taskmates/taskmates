from pathlib import Path

from typing_extensions import override

from taskmates.contexts import default_taskmates_dirs, Contexts
from taskmates.sdk import TaskmatesExtension


class TaskmatesDirLoader(TaskmatesExtension):
    @override
    def after_build_contexts(self, contexts: Contexts):
        local_taskmates_dir = str(Path(contexts["completion_context"]["cwd"]) / ".taskmates")
        overridden_taskmates_dirs = contexts["completion_opts"].get("taskmates_dirs", None)
        effective_taskmates_dirs = overridden_taskmates_dirs or [local_taskmates_dir, *default_taskmates_dirs]
        contexts["completion_opts"]["taskmates_dirs"] = effective_taskmates_dirs
