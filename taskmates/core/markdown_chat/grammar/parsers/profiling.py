import os
from contextlib import contextmanager
from typing import Optional

from taskmates.core.markdown_chat.grammar.parsers.pyparsing_profiler import ParserProfiler

_profiler: Optional[ParserProfiler] = None


def get_profiler() -> Optional[ParserProfiler]:
    """Get the global profiler instance if profiling is enabled."""
    global _profiler
    if os.getenv('PYPARSING_PROFILE') and _profiler is None:
        _profiler = ParserProfiler()
    return _profiler


@contextmanager
def profile_parser(parser):
    """Context manager to profile a parser if profiling is enabled."""
    profiler = get_profiler()
    if profiler is not None:
        with profiler.profile(parser):
            yield
    else:
        yield


def print_profile_report(test_name: str, min_calls: int = 5):
    """Print profiling report if profiling is enabled."""
    profiler = get_profiler()
    if profiler is not None:
        print(f"\nProfiling results for test: {test_name}")
        print("-" * 100)
        profiler.print_report(min_calls=min_calls, sort_by='total_time')
        profiler.reset()
