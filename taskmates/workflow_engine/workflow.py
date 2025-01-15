from abc import ABC
from typing import Any

import pytest

from taskmates.core.coalesce import coalesce
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.workflow_engine.plan import Plan
from taskmates.workflow_engine.run import RUN, Objective, ObjectiveKey, Run


class Workflow(Plan, ABC):
    async def fulfill(self, **kwargs) -> Any:
        current_run = RUN.get()
        current_objective = current_run.objective

        outcome = to_snake_case(self.__class__.__name__)
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
            context=coalesce(await self.create_context(**kwargs), current_run.context),
            daemons=await self.create_daemons(),
            signals={**current_run.signals, **await self.create_signals()},
            state={**current_run.state, **await self.create_state()}
        )

        return await sub_run.run_steps(self.steps)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@pytest.mark.asyncio
async def test_workflow_execution(context):
    from taskmates.workflow_engine.run import Run

    class TestWorkflow(Workflow):
        async def create_context(self, **kwargs):
            return context

        async def steps(self, **kwargs):
            return sum(kwargs.values())

        async def create_daemons(self):
            return {}

        async def create_signals(self):
            return {}

        async def create_state(self):
            return {}

    workflow = TestWorkflow()
    parent_run = Run(
        objective=Objective(key=ObjectiveKey(outcome="test")),
        context=context,
        signals={},
        state={}
    )

    with parent_run:
        result = await workflow.fulfill(a=1, b=2, c=3)

    assert result == 6
