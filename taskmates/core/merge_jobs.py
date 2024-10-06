import functools

from taskmates.core.run import jobs_to_dict


def merge_jobs(*jobs):
    return functools.reduce(lambda x, y: {**x, **y}, map(jobs_to_dict, jobs))
