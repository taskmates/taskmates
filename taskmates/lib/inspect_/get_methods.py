import inspect


def get_methods(module) -> list[str]:
    return [method for method in dir(module) if callable(getattr(module, method))
            and (inspect.ismethod(getattr(module, method)) or inspect.isfunction(getattr(module, method)))]
