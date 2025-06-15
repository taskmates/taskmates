import inspect
from types import FrameType

from typing import TypedDict, Optional, Callable


class CallerInfo(TypedDict):
    function: str
    filename: str
    lineno: int
    instance: Optional[object]


def first_non_private(frame: FrameType, level: int) -> bool:
    function_name: str = inspect.getframeinfo(frame).function
    return level >= 2 and not function_name.startswith('_')


def get_caller_info(stop_condition: Callable[[FrameType, int], bool] = first_non_private) -> CallerInfo:
    frame = inspect.currentframe()
    level = 0
    while frame.f_back and not stop_condition(frame, level):
        frame = frame.f_back
        level += 1

    caller_info = inspect.getframeinfo(frame)
    caller_locals = frame.f_locals
    instance = caller_locals.get('self', None)

    return {
        'function': caller_info.function,
        'filename': caller_info.filename,
        'lineno': caller_info.lineno,
        'instance': instance,
    }


# Test cases

class TestClass:
    def test_instance_method(self):
        info = get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))
        assert info['function'] == 'test_instance_method'
        assert isinstance(info['instance'], TestClass)


def test_regular_function():
    info = get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))
    assert info['function'] == 'test_regular_function'
    assert info['instance'] is None


def test_nested_function():
    def inner_function():
        return get_caller_info(lambda frame, level: level >= 1)

    info = inner_function()
    assert info['function'] == 'inner_function'
    assert info['instance'] is None


def test_lambda_function():
    lambda_func = lambda: get_caller_info(lambda frame, level: level >= 1) # noqa: E731
    info = lambda_func()
    assert info['function'] == '<lambda>'
    assert info['instance'] is None


def test_different_levels():
    def level1():
        return level2()

    def level2():
        return level3()

    def level3():
        return get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))

    info = level1()
    assert info['function'] == 'test_different_levels'


def test_file_info():
    info = get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))
    assert 'get_caller_info.py' in info['filename']
    assert isinstance(info['lineno'], int)


def test_various_levels():
    def inner_function():
        return get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))

    info = inner_function()
    assert info['function'] == 'test_various_levels'


def test_top_of_stack():
    def go_to_top(current_level=0):
        if current_level < 100:  # Arbitrary large number
            return go_to_top(current_level + 1)
        return get_caller_info(lambda frame, level: frame.f_code.co_name.startswith('test_'))

    info = go_to_top()
    assert info['function'] == 'test_top_of_stack'


# Additional test for custom stop condition
def test_custom_stop_condition():
    def custom_function():
        return get_caller_info(lambda frame, level: frame.f_code.co_name == 'test_custom_stop_condition')

    info = custom_function()
    assert info['function'] == 'test_custom_stop_condition'
