def _filtered_wrapper(conditional_wrapper, filter_fn):
    def _wrapper(wrapped, instance, args, kwargs):
        if filter_fn(wrapped, instance, args, kwargs):
            return conditional_wrapper(wrapped, instance, args, kwargs)
        else:
            return wrapped(*args, **kwargs)

    return _wrapper
