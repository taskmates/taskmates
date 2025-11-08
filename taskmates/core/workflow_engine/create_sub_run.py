from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflow_engine.objective import ObjectiveKey, Objective


def create_sub_run(current_run: Transaction, outcome: str, inputs=None):
    current_objective = current_run.objective
    sub_objective = Objective(
        of=current_objective,
        key=ObjectiveKey(
            outcome=outcome,
            inputs=inputs or {},
            requesting_run=current_run
        ))
    current_objective.sub_objectives[sub_objective.key] = sub_objective
    sub_run = Transaction(objective=sub_objective,
                          context=current_run.context.copy())
    return sub_run
