import fnmatch


def is_path_allowed(path, allow_pattern, deny_pattern):
    """
    Check if a path is allowed based on allow and deny patterns.

    :param path: Path to check
    :param allow_pattern: Pattern for allowed paths
    :param deny_pattern: Pattern for denied paths
    :return: True if path is allowed, False otherwise
    """
    path_str = str(path)
    if deny_pattern and fnmatch.fnmatch(path_str, deny_pattern):
        return False
    return fnmatch.fnmatch(path_str, allow_pattern)
