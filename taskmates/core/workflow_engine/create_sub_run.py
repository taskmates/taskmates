from taskmates.core.workflow_engine.run import Objective, ObjectiveKey, Run


def create_sub_run(current_run: Run, outcome: str, inputs=None):
    current_objective = current_run.objective
    sub_objective = Objective(
        of=current_objective,
        key=ObjectiveKey(
            outcome=outcome,
            inputs=inputs or {},
            requesting_run=current_run
        ))
    current_objective.sub_objectives[sub_objective.key] = sub_objective
    sub_run = Run(objective=sub_objective,
                  context=current_run.context,
                  daemons={},
                  signals=current_run.signals,
                  state=current_run.state)
    return sub_run
