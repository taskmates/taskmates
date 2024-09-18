import os
from datetime import datetime
from pathlib import Path

from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.resources_.resources import dump_resource
from taskmates.core.processor import Processor


class FileSystemArtifactsSink(Processor):

    # TODO: logic for enabling/disabling handlers

    @staticmethod
    async def handle_artifact(sender):
        # TODO: this is the part that is confusing
        # Maybe we should get an artifacts_dir instead

        taskmates_home = Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")))
        request_id = EXECUTION_CONTEXT.get().contexts["completion_context"]["request_id"]

        # The problem seems to be that we're mixing artifacts and logs

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        full_path = Path(taskmates_home) / "logs" / f"[{request_id}][{timestamp}] {sender.get('name')}"
        dump_resource(full_path, sender.get('content'))

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.artifact.artifact.connect(self.handle_artifact, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.artifact.artifact.disconnect(self.handle_artifact)
