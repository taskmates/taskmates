from abc import ABC
from typing import Any

import pytest

from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.workflow_engine.plan import Plan
from taskmates.workflow_engine.run import RUN, Objective, ObjectiveKey


class Workflow(Plan, ABC):
    async def fulfill(self, **kwargs) -> Any:
        current_run = RUN.get()

        outcome = to_snake_case(self.__class__.__name__)
        sub_objective = Objective(key=ObjectiveKey(
            outcome=outcome,
            inputs=kwargs or {},  # Use empty dict if inputs is None
            requesting_run=current_run
        ))
        return await (sub_objective
        .attempt(
            context=await self.create_context(**kwargs),
            daemons=await self.create_daemons(),
            state=await self.create_state(),
            signals=await self.create_signals(),
        )).run_steps(self.steps)

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
