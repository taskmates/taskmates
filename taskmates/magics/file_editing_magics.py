from pathlib import Path

from IPython.core.magic import (Magics, magics_class, cell_magic)

@magics_class
class FileEditingMagics(Magics):
    def __init__(self, *args, **kwargs):
        super(FileEditingMagics, self).__init__(*args, **kwargs)
        self.state = {"filename": None, "text_to_replace": None}

    @cell_magic
    def match_content_block_to_replace(self, line, cell):
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
    def replace_matched_content_block(self, line, cell):
        filename = line.strip()
        new_text = cell

        if filename != self.state["filename"]:
            raise ValueError("Filename mismatch or `match_content_block_to_replace` not called before `replace_matched_content_block`.")

        with open(filename, 'r') as f:
            content = f.read()

        updated_content = content.replace(self.state["text_to_replace"], new_text, 1)

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
