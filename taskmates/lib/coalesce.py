def coalesce(*args):
    """Return the first non-None value from the arguments, or None if all are None."""
    for arg in args:
        if arg is not None:
            return arg
    return None
