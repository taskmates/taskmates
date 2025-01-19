from taskmates.workflow_engine.environment_signals import EnvironmentSignals
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.input_streams import InputStreams
from taskmates.workflows.signals.output_streams import OutputStreams
from taskmates.workflows.signals.status_signals import StatusSignals


def default_environment_signals() -> EnvironmentSignals:
    return {
        'control': ControlSignals(),
        'status': StatusSignals(),
        'input_streams': InputStreams(),
        'output_streams': OutputStreams()
    }
