from abc import ABC
from contextlib import AbstractContextManager
from typing import Any
from typing import Optional

import pytest

from taskmates.core.coalesce import coalesce
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.workflow_engine.create_sub_run import create_sub_run
from taskmates.workflow_engine.plan import Plan
from taskmates.workflow_engine.run import RUN, Objective, ObjectiveKey, Run
from taskmates.workflows.contexts.run_context import RunContext


class Workflow(Plan, ABC):
    def __init__(self,
                 context: Optional[RunContext] = None,
                 signals: Optional[dict[str, Any]] = None,
                 daemons: Optional[dict[str, AbstractContextManager]] = None,
                 state: Optional[dict[str, Any]] = None):
        self.context = context
        self.signals = signals or {}
        self.daemons = daemons or {}
        self.state = state or {}

    async def fulfill(self, **kwargs) -> Any:
        workflow_name = to_snake_case(self.__class__.__name__)

        with create_sub_run(RUN.get(), f"{self.__class__.__name__}.fulfill", kwargs):
            current_run = RUN.get()
            current_objective = current_run.objective

            outcome = f"{self.__class__.__name__}.run_steps"
            sub_objective = Objective(
                of=current_objective,
                key=ObjectiveKey(
                    outcome=outcome,
                    inputs=kwargs or {},
                    requesting_run=current_run
                ))
            current_objective.sub_objectives[sub_objective.key] = sub_objective

            sub_run = Run(
                objective=sub_objective,
                context=coalesce(self.context, current_run.context),
                daemons=self.daemons,
                signals={**current_run.signals, **self.signals},
                state={**current_run.state, **self.state}
            )

            return await sub_run.run_steps(self.steps)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@pytest.mark.asyncio
async def test_workflow_execution(context):
    from taskmates.workflow_engine.run import Run

    class TestWorkflow(Workflow):
        async def steps(self, **kwargs):
            return sum(kwargs.values())

    workflow = TestWorkflow(context=context)
    parent_run = Run(
        objective=Objective(key=ObjectiveKey(outcome="test")),
        context=context,
        signals={},
        state={}
    )

    with parent_run:
        result = await workflow.fulfill(a=1, b=2, c=3)

    assert result == 6
