from contextlib import contextmanager, ExitStack, AbstractContextManager
from typing import Sequence


@contextmanager
def stacked_contexts(cms: Sequence[AbstractContextManager]):
    with ExitStack() as stack:
        try:
            yield [stack.enter_context(cm) for cm in cms]
        except Exception as e:
            print(e)
            raise e
