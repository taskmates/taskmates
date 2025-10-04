import functools

from taskmates.core.workflow_engine.transaction import to_daemons_dict


def merge_jobs(*jobs):
    return functools.reduce(lambda x, y: {**x, **y}, map(to_daemons_dict, jobs))
