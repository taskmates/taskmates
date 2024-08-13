import os
from datetime import datetime
from pathlib import Path

from taskmates.contexts import CONTEXTS
from taskmates.lib.resources_.resources import dump_resource
from taskmates.core.signal_receiver import SignalReceiver
from taskmates.signals.signals import Signals


class FileSystemArtifactsSink(SignalReceiver):

    # TODO: logic for enabling/disabling handlers

    @staticmethod
    async def handle_artifact(sender):
        # TODO: this is the part that is confusing
        # Maybe we should get an artifacts_dir instead

        taskmates_home = Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")))
        request_id = CONTEXTS.get()["completion_context"]["request_id"]

        # The problem seems to be that we're mixing artifacts and logs

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        full_path = Path(taskmates_home) / "logs" / f"[{request_id}][{timestamp}] {sender.get('name')}"
        dump_resource(full_path, sender.get('content'))

    def connect(self, signals: Signals):
        signals.output.artifact.connect(self.handle_artifact, weak=False)

    def disconnect(self, signals: Signals):
        signals.output.artifact.disconnect(self.handle_artifact)
