from blinker import Signal
from ordered_set import OrderedSet

from taskmates.core.signals.artifact_signals import ArtifactSignals
from taskmates.core.signals.control_signals import ControlSignals
from taskmates.core.signals.input_signals import CliInputSignals
from taskmates.core.signals.lifecycle_signals import LifecycleSignals
from taskmates.core.signals.response_signals import ResponseSignals

Signal.set_class = OrderedSet


class SignalsContext:
    def __init__(self):
        self.control = ControlSignals()
        self.cli_input = CliInputSignals()

        self.lifecycle = LifecycleSignals()
        self.response = ResponseSignals()
        self.artifact = ArtifactSignals()
