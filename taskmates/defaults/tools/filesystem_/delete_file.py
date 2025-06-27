import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.run import RUN


def delete_file(path):
    """
    Deletes a file from the user's machine
    :param path: the path to the file to delete
    :return: None
    """

    contexts = RUN.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("delete_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("delete_file") or {}).get("deny", None)

    path_obj = Path(path)
    if not path_obj.is_file():
        print(f"The path '{path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(path_obj, allow, deny):
        print(f"Access to file '{path}' is not allowed.", file=sys.stderr)
        return None

    path_obj.unlink()
    return None


def test_delete_file_removes_existing_file(tmp_path):
    from unittest.mock import Mock, patch
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Content to delete")
    
    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "delete_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.delete_file.RUN', mock_run):
        delete_file(str(test_file))
    
    assert not test_file.exists()


def test_delete_file_returns_none_for_non_existent_file(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    non_existent = tmp_path / "non_existent.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "delete_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.delete_file.RUN', mock_run):
        result = delete_file(str(non_existent))
    
    assert result is None
    captured = capsys.readouterr()
    assert "is not a file or does not exist" in captured.err


def test_delete_file_respects_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("Content")
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "delete_file": {
                    "allow": "**",
                    "deny": "*.txt"
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.delete_file.RUN', mock_run):
        with patch('taskmates.defaults.tools.filesystem_.delete_file.is_path_allowed', return_value=False):
            result = delete_file(str(test_file))
    
    assert result is None
    assert test_file.exists()  # File should still exist
    captured = capsys.readouterr()
    assert "Access to file" in captured.err
    assert "is not allowed" in captured.err


def test_delete_file_handles_directory_path(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "delete_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.delete_file.RUN', mock_run):
        result = delete_file(str(test_dir))
    
    assert result is None
    assert test_dir.exists()  # Directory should still exist
    captured = capsys.readouterr()
    assert "is not a file or does not exist" in captured.err
