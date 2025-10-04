from abc import ABC
from contextlib import AbstractContextManager
from typing import Any
from typing import Optional

import pytest

from taskmates.core.workflow_engine.create_sub_run import create_sub_run
from taskmates.core.workflow_engine.plan import Plan
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflow_engine.transaction import TRANSACTION, Objective, ObjectiveKey, Transaction
from taskmates.lib.coalesce import coalesce
from taskmates.lib.str_.to_snake_case import to_snake_case


class Workflow(Plan, ABC):
    def __init__(self,
                 context: Optional[RunContext] = None,
                 emits: Optional[dict[str, Any]] = None,
                 consumes: Optional[dict[str, Any]] = None,
                 daemons: Optional[dict[str, AbstractContextManager]] = None,
                 state: Optional[dict[str, Any]] = None):
        self.context = context
        self.emits = emits or {}
        self.consumes = consumes or {}
        self.daemons = daemons or {}
        self.state = state or {}

    async def fulfill(self, **kwargs) -> Any:
        to_snake_case(self.__class__.__name__)

        async with create_sub_run(TRANSACTION.get(), f"{self.__class__.__name__}.fulfill",
                                  kwargs).async_transaction_context():
            current_run = TRANSACTION.get()
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

            sub_run = Transaction(
                objective=sub_objective,
                context=coalesce(self.context, current_run.execution_context.consumes),
                daemons=self.daemons,
                emits={**current_run.execution_context.emits, **self.emits},
                consumes={**current_run.execution_context.consumes, **self.consumes},
                state={**current_run.execution_context.state, **self.state}
            )

            return await sub_run.run_steps(self.steps)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@pytest.mark.asyncio
async def test_workflow_execution(context, run: Transaction):
    class TestWorkflow(Workflow):
        async def steps(self, **kwargs):
            return sum(kwargs.values())

    workflow = TestWorkflow(context=context)

    async with run.async_transaction_context():
        result = await workflow.fulfill(a=1, b=2, c=3)

    assert result == 6
