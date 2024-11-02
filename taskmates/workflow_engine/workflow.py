from abc import ABC
from typing import Any

import pytest
from opentelemetry import trace

from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.workflow_engine.plan import Plan
from taskmates.workflow_engine.run import RUN
from taskmates.workflow_engine.runner import Runner


class Workflow(Plan, ABC):
    async def fulfill(self, **kwargs) -> Any:
        inputs = kwargs

        parent_attempt = RUN.get()

        objective = parent_attempt.request(
            outcome=to_snake_case(self.__class__.__name__),
            inputs=inputs)

        context = await self.create_context(**kwargs)

        run = objective.attempt(
            context=context,
            daemons=await self.create_daemons(),
            state=await self.create_state(),
            signals=await self.create_signals(),
        )

        # TODO: interesting...
        objective.last_run = run
        objective.runs.append(objective.last_run)

        runner = Runner(func=self.steps, inputs=inputs)

        with tracer().start_as_current_span(format_span_name(self.steps, self),
                                            kind=trace.SpanKind.INTERNAL):
            with run:
                runner.start()
                # if kwargs.get('return_run', False):
                #     return requester
                return await runner.get_result()

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@pytest.mark.asyncio
async def test_workflow_execution(context):
    from taskmates.workflow_engine.run import Run
    from taskmates.workflow_engine.objective import Objective

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
        objective=Objective(outcome="test"),
        context=context,
        signals={},
        state={},
        results={}
    )

    with parent_run:
        result = await workflow.fulfill(a=1, b=2, c=3)

    assert result == 6
