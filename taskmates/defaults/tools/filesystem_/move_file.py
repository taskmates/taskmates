import sys
from pathlib import Path

from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed
from taskmates.core.workflow_engine.run import RUN


def move_file(source_path, destination_path):
    """
    Moves or renames a file on the user's machine
    :param source_path: the source file path
    :param destination_path: the destination file path
    :return: None
    """

    contexts = RUN.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("move_file") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("move_file") or {}).get("deny", None)

    source_obj = Path(source_path)
    dest_obj = Path(destination_path)
    
    if not source_obj.is_file():
        print(f"The source path '{source_path}' is not a file or does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(source_obj, allow, deny):
        print(f"Access to source file '{source_path}' is not allowed.", file=sys.stderr)
        return None
        
    if not is_path_allowed(dest_obj, allow, deny):
        print(f"Access to destination path '{destination_path}' is not allowed.", file=sys.stderr)
        return None

    # Create destination directory if it doesn't exist
    dest_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # Move the file
    source_obj.rename(dest_obj)
    return None


def test_move_file_moves_file_to_new_location(tmp_path):
    from unittest.mock import Mock, patch
    
    # Create source file
    source_file = tmp_path / "source.txt"
    source_file.write_text("File content")
    
    # Define destination
    dest_file = tmp_path / "subdir" / "destination.txt"
    
    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move_file(str(source_file), str(dest_file))
    
    assert not source_file.exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "File content"


def test_move_file_renames_file_in_same_directory(tmp_path):
    from unittest.mock import Mock, patch
    
    # Create source file
    source_file = tmp_path / "old_name.txt"
    source_file.write_text("File content")
    
    # Define destination
    dest_file = tmp_path / "new_name.txt"
    
    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move_file(str(source_file), str(dest_file))
    
    assert not source_file.exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "File content"


def test_move_file_returns_none_for_non_existent_source(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    non_existent = tmp_path / "non_existent.txt"
    dest_file = tmp_path / "destination.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        result = move_file(str(non_existent), str(dest_file))
    
    assert result is None
    captured = capsys.readouterr()
    assert "is not a file or does not exist" in captured.err


def test_move_file_respects_source_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    source_file = tmp_path / "source.txt"
    source_file.write_text("Content")
    dest_file = tmp_path / "destination.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": "*.txt"
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        with patch('taskmates.defaults.tools.filesystem_.move_file.is_path_allowed', return_value=False):
            result = move_file(str(source_file), str(dest_file))
    
    assert result is None
    assert source_file.exists()  # File should still exist
    captured = capsys.readouterr()
    assert "Access to source file" in captured.err
    assert "is not allowed" in captured.err


def test_move_file_respects_destination_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    source_file = tmp_path / "source.txt"
    source_file.write_text("Content")
    dest_file = tmp_path / "destination.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    def mock_is_path_allowed(path, allow, deny):
        # Allow source, deny destination
        return str(path) == str(source_file)
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        with patch('taskmates.defaults.tools.filesystem_.move_file.is_path_allowed', side_effect=mock_is_path_allowed):
            result = move_file(str(source_file), str(dest_file))
    
    assert result is None
    assert source_file.exists()  # File should still exist
    captured = capsys.readouterr()
    assert "Access to destination path" in captured.err
    assert "is not allowed" in captured.err


def test_move_file_handles_directory_as_source(tmp_path, capsys):
    from unittest.mock import Mock, patch
    
    source_dir = tmp_path / "sourcedir"
    source_dir.mkdir()
    dest_file = tmp_path / "destination.txt"
    
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move_file": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }
    
    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        result = move_file(str(source_dir), str(dest_file))
    
    assert result is None
    assert source_dir.exists()  # Directory should still exist
    captured = capsys.readouterr()
    assert "is not a file or does not exist" in captured.err
