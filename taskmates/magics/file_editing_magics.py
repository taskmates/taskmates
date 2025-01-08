from pathlib import Path

import pytest
from IPython.core.magic import (Magics, magics_class, cell_magic)
from IPython.terminal.interactiveshell import TerminalInteractiveShell


@magics_class
class FileEditingMagics(Magics):
    def __init__(self, *args, **kwargs):
        super(FileEditingMagics, self).__init__(*args, **kwargs)
        self.state = {"filename": None, "text_to_replace": None}

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
            raise ValueError(f"Text to replace not found in {filename}. Text:\n{text_to_find}")
        else:
            raise ValueError(f"Multiple occurrences of text to replace found in {filename}.")

    @cell_magic
    def replace_selection(self, line, cell):
        filename = line.strip()
        new_text = cell

        if filename != self.state["filename"]:
            raise ValueError(
                "No selection")

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
            raise ValueError("No selection")

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
            raise ValueError("No selection")

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
            raise ValueError("No selection")

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
                raise FileExistsError(f"File {filename} already exists.")
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


def test_delete_selection_no_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to delete without selection
    with pytest.raises(ValueError, match="No selection"):
        ip.run_cell_magic('delete_selection', str(test_file), ' ')  # non-empty cell


def test_insert_before_selection_no_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to insert before without selection
    with pytest.raises(ValueError, match="No selection"):
        ip.run_cell_magic('insert_before_selection', str(test_file), 'new_line\n')


def test_insert_after_selection_no_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3")

    # Try to insert after without selection
    with pytest.raises(ValueError, match="No selection"):
        ip.run_cell_magic('insert_after_selection', str(test_file), 'new_line\n')
