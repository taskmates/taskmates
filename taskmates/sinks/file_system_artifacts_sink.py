from datetime import datetime
from pathlib import Path

from taskmates.lib.resources_.resources import dump_resource
from taskmates.signals.signals import Signals


class FileSystemArtifactsSink:
    def __init__(self, taskmates_dir, request_id):
        self.taskmates_dir = taskmates_dir
        self.request_id = request_id

    async def handle_artifact(self, sender):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        full_path = Path(self.taskmates_dir) / "logs" / f"[{self.request_id}][{timestamp}] {sender.get('name')}"
        dump_resource(full_path, sender.get('content'))

    def connect(self, signals: Signals):
        signals.output.artifact.connect(self.handle_artifact)
