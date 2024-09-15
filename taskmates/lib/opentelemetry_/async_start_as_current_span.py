from functools import wraps


def async_start_as_current_span(tracer, func=None, *, span_name=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal span_name
            if span_name is None:
                cls = args[0]
                span_name = f"{cls.__name__}.{func.__name__}"
            with tracer().start_as_current_span(span_name):
                return await func(*args, **kwargs)

        return wrapper

    if func is None:
        decorated_function = decorator
    else:
        decorated_function = decorator(func)

    return decorated_function
