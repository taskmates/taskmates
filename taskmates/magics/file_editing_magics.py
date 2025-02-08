import sys
from pathlib import Path

import pytest
from IPython.core.magic import (Magics, magics_class, cell_magic)
from IPython.terminal.interactiveshell import TerminalInteractiveShell


class NotebookExecutionInterrupted(Exception):
    def _render_traceback_(self):
        return []


@magics_class
class FileEditingMagics(Magics):
    def __init__(self, *args, **kwargs):
        super(FileEditingMagics, self).__init__(*args, **kwargs)
        self.state = {"filename": None, "text_to_replace": None}

    def _write_error(self, message):
        print(message, file=sys.stderr, flush=True)
        raise NotebookExecutionInterrupted

    @cell_magic
    def select_text(self, line, cell):
        filename = line.strip()
        text_to_find = cell

        with open(filename, 'r') as f:
            content = f.read()

        if content.count(text_to_find) == 1:
            self.state["filename"] = filename
            self.state["text_to_replace"] = text_to_find
        elif content.count(text_to_find) == 0:
            return self._write_error(
                f"Error: Text not found in {filename}.\n"
                f"Hint: Make sure the text exists in the file and matches exactly, "
                f"including whitespace and newlines. Maybe you tried the incorrect number of whitespaces in the indentation?\n")
        else:
            return self._write_error(
                f"Error: Multiple occurrences of text found in {filename}.\n"
                f"Hint: The text to select must be unique in the file. "
                f"Try selecting a larger portion of text to make it unique.")

    @cell_magic
    def replace_selection(self, line, cell):
        filename = line.strip()
        new_text = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to replace.")

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"], new_text, 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None}

    @cell_magic
    def delete_selection(self, line, cell):
        filename = line.strip()

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to delete.")

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"], "", 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None}

    @cell_magic
    def insert_before_selection(self, line, cell):
        filename = line.strip()
        text_to_insert = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to insert before.")

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"],
                                          text_to_insert + self.state["text_to_replace"], 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None}

    @cell_magic
    def insert_after_selection(self, line, cell):
        filename = line.strip()
        text_to_insert = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to insert after.")

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"],
                                          self.state["text_to_replace"] + text_to_insert, 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None}

    @cell_magic
    def append_to_file(self, line, cell):
        filename = line.strip()
        text_to_append = cell

        with open(filename, 'a') as f:
            f.write(text_to_append)

    @cell_magic
    def create_file(self, line, cell):
        filename = line.strip()
        content = cell

        try:
            with open(filename, 'r'):
                return self._write_error(
                    f"Error: File {filename} already exists.\n"
                    f"Hint: Use %%overwrite_file if you want to replace the existing file.")
        except FileNotFoundError:
            with open(filename, 'w') as f:
                f.write(content)

    @cell_magic
    def overwrite_file(self, line, cell):
        filename = line.strip()
        content = cell

        with open(filename, 'w') as f:
            f.write(content)


def load_ipython_extension(ipython):
    """
    This function is called when the extension is loaded.
    It registers the magic class with IPython.
    """
    ipython.register_magics(FileEditingMagics)


@pytest.fixture
def ip():
    ip = TerminalInteractiveShell()
    ip.register_magics(FileEditingMagics)
    return ip


def test_delete_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Select text
    ip.run_cell_magic('select_text', str(test_file), 'line2\n')

    # Delete selection
    ip.run_cell_magic('delete_selection', str(test_file), ' ')  # non-empty cell

    assert test_file.read_text() == "line1\nline3"


def test_insert_before_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Select text
    ip.run_cell_magic('select_text', str(test_file), 'line2\n')

    # Insert before selection
    ip.run_cell_magic('insert_before_selection', str(test_file), 'new_line\n')

    assert test_file.read_text() == "line1\nnew_line\nline2\nline3"


def test_insert_after_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Select text
    ip.run_cell_magic('select_text', str(test_file), 'line2\n')

    # Insert after selection
    ip.run_cell_magic('insert_after_selection', str(test_file), 'new_line\n')

    assert test_file.read_text() == "line1\nline2\nnew_line\nline3"


def test_delete_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to delete without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('delete_selection', str(test_file), ' ')  # non-empty cell

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_insert_before_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to insert before without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('insert_before_selection', str(test_file), 'new_line\n')

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_insert_after_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to insert after without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('insert_after_selection', str(test_file), 'new_line\n')

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_create_file_already_exists(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content")

    # Try to create the same file
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('create_file', str(test_file), 'new content')

    captured = capsys.readouterr()
    assert "Error: File" in captured.err
    assert "already exists" in captured.err
    assert "Hint: Use %%overwrite_file" in captured.err

    # Original content should remain unchanged
    assert test_file.read_text() == "original content"


def test_select_text_not_found(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to select non-existent text
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('select_text', str(test_file), 'nonexistent\n')

    captured = capsys.readouterr()
    assert "Error: Text not found" in captured.err
    assert "Hint: Make sure the text exists" in captured.err


def test_select_text_multiple_occurrences(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline1\nline3")  # Note: line1 appears twice

    # Try to select text that appears multiple times
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('select_text', str(test_file), 'line1\n')

    captured = capsys.readouterr()
    assert "Error: Multiple occurrences of text found" in captured.err
    assert "Hint: The text to select must be unique" in captured.err
