import sys
from pathlib import Path

from taskmates.core.workflow_engine.run import RUN
from taskmates.defaults.tools.filesystem_.is_path_allowed import is_path_allowed


def move(source_path, destination_path):
    """
    Moves or renames a file or directory on the user's machine
    :param source_path: the source file or directory path
    :param destination_path: the destination path
    :return: None
    """

    contexts = RUN.get().context
    run_opts = contexts["run_opts"]

    allow = ((run_opts.get("tools") or {}).get("move") or {}).get("allow", "**")
    deny = ((run_opts.get("tools") or {}).get("move") or {}).get("deny", None)

    source_obj = Path(source_path)
    dest_obj = Path(destination_path)

    if not source_obj.exists():
        print(f"The source path '{source_path}' does not exist.", file=sys.stderr)
        return None

    if not is_path_allowed(source_obj, allow, deny):
        print(f"Access to source path '{source_path}' is not allowed.", file=sys.stderr)
        return None

    if not is_path_allowed(dest_obj, allow, deny):
        print(f"Access to destination path '{destination_path}' is not allowed.", file=sys.stderr)
        return None

    # Create destination parent directory if it doesn't exist
    dest_obj.parent.mkdir(parents=True, exist_ok=True)

    # Move the file or directory
    source_obj.rename(dest_obj)
    return None


def test_move_moves_file_to_new_location(tmp_path):
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
                "move": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move(str(source_file), str(dest_file))

    assert not source_file.exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "File content"


def test_move_renames_file_in_same_directory(tmp_path):
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
                "move": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move(str(source_file), str(dest_file))

    assert not source_file.exists()
    assert dest_file.exists()
    assert dest_file.read_text() == "File content"


def test_move_moves_directory_to_new_location(tmp_path):
    from unittest.mock import Mock, patch

    # Create source directory with content
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("Content 1")
    (source_dir / "file2.txt").write_text("Content 2")
    subdir = source_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("Content 3")

    # Define destination
    dest_dir = tmp_path / "dest" / "moved_dir"

    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move(str(source_dir), str(dest_dir))

    assert not source_dir.exists()
    assert dest_dir.exists()
    assert (dest_dir / "file1.txt").read_text() == "Content 1"
    assert (dest_dir / "file2.txt").read_text() == "Content 2"
    assert (dest_dir / "subdir" / "file3.txt").read_text() == "Content 3"


def test_move_renames_directory_in_same_location(tmp_path):
    from unittest.mock import Mock, patch

    # Create source directory
    source_dir = tmp_path / "old_dir_name"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("Content")

    # Define destination
    dest_dir = tmp_path / "new_dir_name"

    # Mock RUN context
    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        move(str(source_dir), str(dest_dir))

    assert not source_dir.exists()
    assert dest_dir.exists()
    assert (dest_dir / "file.txt").read_text() == "Content"


def test_move_returns_none_for_non_existent_source(tmp_path, capsys):
    from unittest.mock import Mock, patch

    non_existent = tmp_path / "non_existent"
    dest_path = tmp_path / "destination"

    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move": {
                    "allow": "**",
                    "deny": None
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        result = move(str(non_existent), str(dest_path))

    assert result is None
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_move_respects_source_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch

    source_file = tmp_path / "source.txt"
    source_file.write_text("Content")
    dest_file = tmp_path / "destination.txt"

    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move": {
                    "allow": "**",
                    "deny": "*.txt"
                }
            }
        }
    }

    with patch('taskmates.defaults.tools.filesystem_.move_file.RUN', mock_run):
        with patch('taskmates.defaults.tools.filesystem_.move_file.is_path_allowed', return_value=False):
            result = move(str(source_file), str(dest_file))

    assert result is None
    assert source_file.exists()  # File should still exist
    captured = capsys.readouterr()
    assert "Access to source path" in captured.err
    assert "is not allowed" in captured.err


def test_move_respects_destination_deny_rules(tmp_path, capsys):
    from unittest.mock import Mock, patch

    source_file = tmp_path / "source.txt"
    source_file.write_text("Content")
    dest_file = tmp_path / "destination.txt"

    mock_run = Mock()
    mock_run.get.return_value.context = {
        "run_opts": {
            "tools": {
                "move": {
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
            result = move(str(source_file), str(dest_file))

    assert result is None
    assert source_file.exists()  # File should still exist
    captured = capsys.readouterr()
    assert "Access to destination path" in captured.err
    assert "is not allowed" in captured.err
