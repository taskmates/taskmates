from contextlib import contextmanager, ExitStack, AbstractContextManager


@contextmanager
def stacked_contexts(cms: list[AbstractContextManager]):
    with ExitStack() as stack:
        yield [stack.enter_context(cm) for cm in cms]
