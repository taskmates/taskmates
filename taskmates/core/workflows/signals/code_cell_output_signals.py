from taskmates.core.workflow_engine.base_signals import BaseSignals


class CodeCellOutputSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.code_cell_output = self.namespace.signal('code_cell_output')
