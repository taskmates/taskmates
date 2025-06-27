import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.run import RUN


def append_to_file(path, content):
    """
    Appends content to a file on the user's machine
    :param path: the path
    :param content: the content to append
    :return: None
    """

    contexts = RUN.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("append_to_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("append_to_file") or {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    with open(path_obj, 'a') as f:
        f.write(content)
    return None


def test_append_to_file_appends_content_to_existing_file(tmp_path):
    from unittest.mock import Mock, patch
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content\n")
    
    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "append_to_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.append_to_file.RUN', mock_run):
        append_to_file(str(test_file), "Appended content\n")
    
    assert test_file.read_text() == "Initial content\nAppended content\n"


def test_append_to_file_returns_none_for_non_existent_file(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    non_existent = tmp_path / "non_existent.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "append_to_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.append_to_file.RUN', mock_run):
        result = append_to_file(str(non_existent), "Content")
    
    assert result is None
    captured = capsys.readouterr()
    assert "is not a file or does not exist" in captured.err


def test_append_to_file_respects_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("Initial content")
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "append_to_file": {
                    "allow": "**",
                    "deny": "*.txt"
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.append_to_file.RUN', mock_run):
        with patch('taskmates.defaults.tools.filesystem_.append_to_file.is_path_allowed', return_value=False):
            result = append_to_file(str(test_file), "Content")
    
    assert result is None
    captured = capsys.readouterr()
    assert "Access to file" in captured.err
    assert "is not allowed" in captured.err
