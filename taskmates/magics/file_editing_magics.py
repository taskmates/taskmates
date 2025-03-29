import sys
from pathlib import Path
from textwrap import dedent

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
        self.state = {"filename": None, "text_to_replace": None, "indentation_adjustment": None}

    def _write_error(self, message):
        print(message, file=sys.stderr, flush=True)
        raise NotebookExecutionInterrupted

    def _get_indentation(self, line):
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    def _normalize_for_comparison(self, text):
        """Normalize text for comparison by removing all indentation and normalizing empty lines."""
        lines = text.splitlines()
        result = []
        for line in lines:
            if not line.strip():
                result.append("")  # normalize empty lines to empty string
            else:
                result.append(line.lstrip())  # remove all indentation
        return "\n".join(result)

    def _adjust_indentation(self, text, adjustment):
        """Adjust the indentation of text by the given amount."""
        if adjustment == 0:
            return text

        lines = text.splitlines()
        result = []
        for line in lines:
            if not line.strip():  # Empty or whitespace-only line
                result.append("")
            else:
                current_indent = self._get_indentation(line)
                new_indent = max(0, current_indent - adjustment)
                result.append(" " * new_indent + line.lstrip())
        return "\n".join(result)

    def _find_text_in_content(self, text_to_find, content):
        """Find text in content and calculate indentation adjustment."""
        # First, try with the original text
        if content.count(text_to_find) == 1:
            # Calculate indentation adjustment
            find_first_line = text_to_find.splitlines()[0]
            content_lines = content.splitlines()
            for line in content_lines:
                if line.lstrip() == find_first_line.lstrip():
                    return text_to_find, self._get_indentation(find_first_line) - self._get_indentation(line)

        # Then try with normalized text
        normalized_to_find = self._normalize_for_comparison(text_to_find)
        normalized_content = self._normalize_for_comparison(content)

        # Find the start position of the normalized text
        start_pos = normalized_content.find(normalized_to_find)
        if start_pos == -1:
            return None, None

        # Count occurrences
        if normalized_content.count(normalized_to_find) > 1:
            return None, None

        # Find the line number where the text starts
        content_lines = content.splitlines()
        normalized_lines = normalized_content.splitlines()
        
        line_count = 0
        current_pos = 0
        for line in normalized_lines:
            if current_pos <= start_pos < current_pos + len(line) + 1:
                break
            current_pos += len(line) + 1
            line_count += 1

        # Calculate indentation adjustment
        find_first_line = text_to_find.splitlines()[0]
        content_line = content_lines[line_count]
        adjustment = self._get_indentation(find_first_line) - self._get_indentation(content_line)

        # Extract the original lines with correct indentation
        original_lines = content_lines[line_count:line_count + len(text_to_find.splitlines())]
        return "\n".join(original_lines), adjustment

    @cell_magic
    def select_text(self, line, cell):
        filename = line.strip()
        text_to_find = cell

        with open(filename, 'r') as f:
            content = f.read()

        # Try to find the text
        found_text, adjustment = self._find_text_in_content(text_to_find, content)

        if found_text is None:
            # Check if it's because of multiple matches
            normalized_to_find = self._normalize_for_comparison(text_to_find)
            normalized_content = self._normalize_for_comparison(content)
            if normalized_content.count(normalized_to_find) > 1:
                return self._write_error(
                    f"Error: Multiple occurrences of text found in {filename}.\n"
                    f"Hint: The text to select must be unique in the file. "
                    f"Try selecting a larger portion of text to make it unique.")
            else:
                return self._write_error(
                    f"Error: Text not found in {filename}.\n"
                    f"Hint: Make sure the text exists in the file and matches exactly, "
                    f"including whitespace and newlines.\n")

        self.state["filename"] = filename
        self.state["text_to_replace"] = found_text
        self.state["indentation_adjustment"] = adjustment

    @cell_magic
    def replace_selection(self, line, cell):
        filename = line.strip()
        new_text = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to replace.")

        # Adjust indentation of new text
        if self.state["indentation_adjustment"] is not None:
            new_text = self._adjust_indentation(new_text, self.state["indentation_adjustment"])

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"], new_text, 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None, "indentation_adjustment": None}

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
        self.state = {"filename": None, "text_to_replace": None, "indentation_adjustment": None}

    @cell_magic
    def insert_before_selection(self, line, cell):
        filename = line.strip()
        text_to_insert = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to insert before.")

        # Adjust indentation of text to insert
        if self.state["indentation_adjustment"] is not None:
            text_to_insert = self._adjust_indentation(text_to_insert, self.state["indentation_adjustment"])

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"],
                                          text_to_insert + self.state["text_to_replace"], 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None, "indentation_adjustment": None}

    @cell_magic
    def insert_after_selection(self, line, cell):
        filename = line.strip()
        text_to_insert = cell

        if filename != self.state["filename"]:
            return self._write_error(
                "Error: No active selection.\n"
                "Hint: Use %%select_text first to select the text you want to insert after.")

        # Adjust indentation of text to insert
        if self.state["indentation_adjustment"] is not None:
            text_to_insert = self._adjust_indentation(text_to_insert, self.state["indentation_adjustment"])

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"],
                                          self.state["text_to_replace"] + text_to_insert, 1)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            f.write(updated_content)

        # Reset the state
        self.state = {"filename": None, "text_to_replace": None, "indentation_adjustment": None}

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


def test_extra_indentation_example(ip, tmp_path):
    # Create a test file with a method at root level
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        def my_method():
            print("hello")
    """).lstrip())

    # Try to select with extra indentation, EXACTLY as in the example
    ip.run_cell_magic('select_text', str(test_file), "    def my_method():\n        print(\"hello\")\n")

    # Replace with a new method, also with extra indentation
    ip.run_cell_magic('replace_selection', str(test_file), "    def my_method():\n        print(\"goodbye\")\n")

    # Verify that the indentation was preserved
    assert test_file.read_text() == dedent("""
        def my_method():
            print("goodbye")
    """).lstrip()


def test_delete_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Select text
    ip.run_cell_magic('select_text', str(test_file), "line2\n")

    # Delete selection
    ip.run_cell_magic('delete_selection', str(test_file), ' ')  # non-empty cell

    assert test_file.read_text() == dedent("""
        line1
        line3
    """).lstrip()


def test_insert_before_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Select text
    ip.run_cell_magic('select_text', str(test_file), "line2\n")

    # Insert before selection
    ip.run_cell_magic('insert_before_selection', str(test_file), "new_line\n")

    assert test_file.read_text() == dedent("""
        line1
        new_line
        line2
        line3
    """).lstrip()


def test_insert_after_selection(ip, tmp_path):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Select text
    ip.run_cell_magic('select_text', str(test_file), "line2\n")

    # Insert after selection
    ip.run_cell_magic('insert_after_selection', str(test_file), "new_line\n")

    assert test_file.read_text() == dedent("""
        line1
        line2
        new_line
        line3
    """).lstrip()


def test_delete_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Try to delete without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('delete_selection', str(test_file), ' ')  # non-empty cell

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_insert_before_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Try to insert before without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('insert_before_selection', str(test_file), "new_line\n")

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_insert_after_selection_no_selection(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Try to insert after without selection
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('insert_after_selection', str(test_file), "new_line\n")

    captured = capsys.readouterr()
    assert "Error: No active selection" in captured.err
    assert "Hint: Use %%select_text first" in captured.err


def test_create_file_already_exists(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content")

    # Try to create the same file
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('create_file', str(test_file), "new content")

    captured = capsys.readouterr()
    assert "Error: File" in captured.err
    assert "already exists" in captured.err
    assert "Hint: Use %%overwrite_file" in captured.err

    # Original content should remain unchanged
    assert test_file.read_text() == "original content"


def test_select_text_not_found(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line2
        line3
    """).lstrip())

    # Try to select non-existent text
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('select_text', str(test_file), "nonexistent\n")

    captured = capsys.readouterr()
    assert "Error: Text not found" in captured.err
    assert "Hint: Make sure the text exists" in captured.err


def test_select_text_multiple_occurrences(ip, tmp_path, capsys):
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        line1
        line1
        line3
    """).lstrip())  # Note: line1 appears twice

    # Try to select text that appears multiple times
    with pytest.raises(NotebookExecutionInterrupted):
        ip.run_cell_magic('select_text', str(test_file), "line1\n")

    captured = capsys.readouterr()
    assert "Error: Multiple occurrences of text found" in captured.err
    assert "Hint: The text to select must be unique" in captured.err


def test_empty_line_indentation(ip, tmp_path):
    # Create a test file with a method that has empty lines with indentation
    test_file = tmp_path / "test.txt"
    test_file.write_text(dedent("""
        def my_method():
            print("hello 1")
            
            print("hello 2")
    """).lstrip())

    # Try to select with empty line without indentation
    ip.run_cell_magic('select_text', str(test_file),
                      "    def my_method():\n        print(\"hello 1\")\n\n        print(\"hello 2\")\n")

    # Replace with a new method
    ip.run_cell_magic('replace_selection', str(test_file),
                      "    def my_method():\n        print(\"goodbye 1\")\n\n        print(\"goodbye 2\")\n")

    # Verify that the indentation was preserved
    assert test_file.read_text() == dedent("""
        def my_method():
            print("goodbye 1")
            
            print("goodbye 2")
    """).lstrip()


def test_select_text_partial_content(ip, tmp_path):
    # Create a test file with the exact content from the bug report
    test_file = tmp_path / "test.txt"
    test_file.write_text("""\
def test_map_entries_simple_value(graph: Neo4jGraph):
    # Create a simple connection with a string value
    connection = Connection.root()
    connection.computation_future.set_result("test_value")

    entries = graph.map_entries(connection)

    # Verify structure
    assert "nodes" in entries
    assert "edges" in entries
    
    # Verify nodes
    assert len(entries["nodes"]) == 2  # One connection, one thing
    
    # Find connection node
    connection_node = next(n for n in entries["nodes"] if "connection" in n["labels"])
    assert "hardlink" in connection_node["labels"]
    assert connection_node["props"]["uuid"] == ""
    assert connection_node["props"]["signal"] == '{"key": ""}'
    
    # Find thing node
    thing_node = next(n for n in entries["nodes"] if "thing" in n["labels"])
    assert thing_node["props"]["label"] == "'test_value'"
    
    # Verify edges
    assert len(entries["edges"]) == 1  # One leads_to edge
    edge = entries["edges"][0]
    assert edge["from_uuid"] == ""  # Root connection uuid
    assert edge["to_uuid"] == thing_node["props"]["uuid"]
    assert edge["type"] == "leads_to"
""")

    # Try to select partial content, exactly as shown in the bug report
    ip.run_cell_magic('select_text', str(test_file),
"""\
    def test_map_entries_simple_value(graph: Neo4jGraph):
        # Create a simple connection with a string value
        connection = Connection.root()
        connection.computation_future.set_result("test_value")
        
        entries = graph.map_entries(connection)

        # Verify structure
        assert "nodes" in entries
        assert "edges" in entries

        # Verify nodes
        assert len(entries["nodes"]) == 2  # One connection, one thing
""")
