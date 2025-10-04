from typeguard import typechecked

from taskmates.core.workflow_engine.base_signals import connected_signals
from taskmates.core.workflow_engine.transaction import Transaction


@typechecked
def bound_contexts(parent_context: Transaction, child_context: Transaction):
    return connected_signals(
        [
            (parent_context.emits["control"], child_context.emits["control"]),
            (parent_context.emits["input_streams"], child_context.emits["input_streams"]),
            (child_context.consumes["status"], parent_context.consumes["status"]),
            (child_context.consumes["execution_environment"], parent_context.consumes["execution_environment"])
        ])
