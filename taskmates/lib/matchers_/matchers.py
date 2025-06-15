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
