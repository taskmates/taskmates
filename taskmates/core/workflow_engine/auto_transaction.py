import asyncio
from functools import wraps
from typing import Callable

from taskmates.core.workflow_engine.transaction import Transaction


def auto_transaction():
    def decorator(fn: Callable):
        @wraps(fn)
        async def _transaction_wrapper(owner):
            # objective = owner.objective
            # context = owner.context
            # state = owner.state
            # signals = owner.signals
            # daemons = owner.daemons
            #
            # forked_run = Run(
            #     objective=objective,
            #     context=context,
            #     signals=signals,
            #     daemons=daemons,
            #     state=state
            # )

            # with forked_run:
            if asyncio.iscoroutinefunction(fn):
                return await fn(owner)
            return fn(owner)

        return _transaction_wrapper

    return decorator
