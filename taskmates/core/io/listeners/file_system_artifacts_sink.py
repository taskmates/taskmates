import os
from datetime import datetime
from pathlib import Path

from taskmates.core.daemon import Daemon
from taskmates.core.run import RUN
from taskmates.lib.resources_.resources import dump_resource
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class FileSystemArtifactsSink(Daemon):

    # TODO: logic for enabling/disabling handlers

    @staticmethod
    async def handle_artifact(sender):
        # TODO: this is the part that is confusing
        # Maybe we should get an artifacts_dir instead

        taskmates_home = Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")))
        request_id = RUN.get().contexts["completion_context"]["request_id"]

        # The problem seems to be that we're mixing artifacts and logs

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        full_path = Path(taskmates_home) / "logs" / f"[{request_id}][{timestamp}] {sender.get('name')}"
        dump_resource(full_path, sender.get('content'))

    def __enter__(self):
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.output_streams.artifact.connected_to(self.handle_artifact)
        ]))
