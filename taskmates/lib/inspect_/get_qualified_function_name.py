import inspect


def get_qualified_function_name(obj):
    module = inspect.getmodule(obj)
    if module:
        return module.__name__ + '.' + obj.__qualname__
    else:
        return obj.__qualname__
