from contextlib import contextmanager, ExitStack, AbstractContextManager, asynccontextmanager, AsyncExitStack, \
    AbstractAsyncContextManager
from typing import Sequence


@contextmanager
def stacked_contexts(cms: Sequence[AbstractContextManager]):
    with ExitStack() as stack:
        try:
            yield [stack.enter_context(cm) for cm in cms]
        except Exception as e:
            print(e)
            raise e


@asynccontextmanager
async def async_stacked_contexts(cms: Sequence[AbstractAsyncContextManager]):
    async with AsyncExitStack() as stack:
        try:
            contexts = []
            for cm in cms:
                context = await stack.enter_async_context(cm)
                contexts.append(context)
            yield contexts
        except Exception as e:
            print(e)
            raise e
