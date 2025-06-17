"""
Matchers Library
================

This module provides flexible matchers for use in tests and assertions. Matchers allow you to 
express complex conditions in a readable way, particularly useful when you want to check that 
a value meets certain criteria without requiring exact equality.

Usage Examples
--------------

Basic Matchers:
    >>> from taskmates.lib.matchers_ import *
    
    >>> # Check if a value satisfies a condition
    >>> assert "hello" == satisfies(lambda x: len(x) > 3)
    >>> assert 42 == satisfies(lambda x: x > 0 and x < 100)
    
    >>> # Use convenience matchers for common types
    >>> assert "world" == any_string
    >>> assert 123 == any_int
    >>> assert {"key": "value"} == any_dict
    >>> assert [1, 2, 3] == any_list
    
    >>> # Match anything
    >>> assert "literally anything" == anything()
    >>> assert None == anything()

Dict Matching:
    >>> # Check if a dict contains expected key-value pairs (ignores extra keys)
    >>> actual = {"name": "John", "age": 30, "city": "NYC"}
    >>> assert actual == dict_containing({"name": "John", "age": 30})
    
    >>> # Nested dict matching
    >>> actual = {"user": {"id": 123, "name": "Jane", "active": True}}
    >>> assert actual == dict_containing({
    ...     "user": dict_containing({"id": 123, "active": True})
    ... })
    
    >>> # Combine with other matchers
    >>> assert {"count": 5, "message": "Hello"} == dict_containing({
    ...     "count": satisfies(lambda x: x > 0),
    ...     "message": any_string
    ... })

Object Attribute Matching:
    >>> # Check if an object has specific attributes
    >>> class User:
    ...     def __init__(self, name, age):
    ...         self.name = name
    ...         self.age = age
    ...         self.id = 12345
    
    >>> user = User("Alice", 25)
    >>> assert user == object_with_attrs(name="Alice", age=25)
    >>> assert user == object_with_attrs(age=satisfies(lambda x: x >= 18))

JSON Matching:
    >>> # Compare JSON strings by their parsed content (ignores formatting)
    >>> json1 = '{"name": "Bob", "age": 30}'
    >>> json2 = '{"age":30,"name":"Bob"}'  # Different formatting, same content
    >>> assert json2 == json_matching(json1)

Advanced Combinations:
    >>> # Complex nested matching
    >>> response = {
    ...     "status": "success",
    ...     "data": {
    ...         "users": [
    ...             {"id": 1, "name": "User1", "email": "user1@example.com"},
    ...             {"id": 2, "name": "User2", "email": "user2@example.com"}
    ...         ],
    ...         "total": 2
    ...     },
    ...     "timestamp": "2024-01-01T00:00:00Z"
    ... }
    >>> 
    >>> assert response == dict_containing({
    ...     "status": "success",
    ...     "data": dict_containing({
    ...         "users": satisfies(lambda x: len(x) == 2),
    ...         "total": any_int
    ...     })
    ... })

Use in Pytest:
    >>> # Matchers work great with pytest assertions
    >>> def test_api_response():
    ...     response = make_api_call()
    ...     assert response == dict_containing({
    ...         "success": True,
    ...         "data": any_dict,
    ...         "timestamp": any_string
    ...     })

Available Matchers
------------------
- satisfies(condition): Match values that satisfy a custom condition function
- dict_containing(expected): Match dicts containing at least the expected key-value pairs
- anything(): Match any value
- json_matching(expected_json_str): Match JSON strings by their parsed content
- object_with_attrs(**attrs): Match objects with specific attribute values
- any_string: Match any string value
- any_int: Match any integer value
- any_dict: Match any dictionary
- any_list: Match any list
"""

def satisfies(condition):
    class Matcher:
        def __eq__(self, other):
            return condition(other)
        
        def __repr__(self):
            return f"satisfies({condition.__name__ if hasattr(condition, '__name__') else 'condition'})"
    
    return Matcher()


def dict_containing(expected):
    """Matcher that checks if a dict contains all expected key-value pairs.
    
    The actual dict may have additional keys that are not checked.
    Nested dicts are also checked recursively.
    """
    class DictContainingMatcher:
        def __eq__(self, other):
            if not isinstance(other, dict):
                return False
            
            for key, expected_value in expected.items():
                if key not in other:
                    return False
                
                actual_value = other[key]
                
                # Handle nested dict_containing matchers
                if isinstance(expected_value, DictContainingMatcher):
                    if not expected_value == actual_value:
                        return False
                # Handle other matchers (like satisfies)
                elif hasattr(expected_value, '__eq__') and expected_value.__class__.__module__ == __name__:
                    if not expected_value == actual_value:
                        return False
                # Handle regular values
                else:
                    if actual_value != expected_value:
                        return False
            
            return True
        
        def __repr__(self):
            return f"dict_containing({expected!r})"
    
    return DictContainingMatcher()


def anything():
    """Matcher that matches any value."""
    return satisfies(lambda x: True)


def json_matching(expected_json_str):
    """Matcher that compares JSON strings by their parsed content."""
    import json
    
    class JsonMatcher:
        def __eq__(self, other):
            if not isinstance(other, str):
                return False
            try:
                return json.loads(expected_json_str) == json.loads(other)
            except (json.JSONDecodeError, TypeError):
                return False
        
        def __repr__(self):
            return f"json_matching({expected_json_str!r})"
    
    return JsonMatcher()


def object_with_attrs(**expected_attrs):
    """Matcher that checks if an object has specific attribute values.
    
    Only checks the specified attributes, ignoring others.
    """
    class ObjectWithAttrsMatcher:
        def __eq__(self, other):
            for attr_name, expected_value in expected_attrs.items():
                if not hasattr(other, attr_name):
                    return False
                
                actual_value = getattr(other, attr_name)
                
                # Handle matchers
                if hasattr(expected_value, '__eq__') and expected_value.__class__.__module__ == __name__:
                    if not expected_value == actual_value:
                        return False
                # Handle regular values
                else:
                    if actual_value != expected_value:
                        return False
            
            return True
        
        def __repr__(self):
            attrs_str = ', '.join(f'{k}={v!r}' for k, v in expected_attrs.items())
            return f"object_with_attrs({attrs_str})"
        
        def __str__(self):
            return self.__repr__()
    
    return ObjectWithAttrsMatcher()

# Convenience instances
any_string = satisfies(lambda x: isinstance(x, str))
any_int = satisfies(lambda x: isinstance(x, int))
any_dict = satisfies(lambda x: isinstance(x, dict))
any_list = satisfies(lambda x: isinstance(x, list))
