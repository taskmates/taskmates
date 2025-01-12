import os
import tempfile
from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger


class BashScriptHandler:
    """Handles the conversion of %%bash cells into executable scripts."""

    def convert_if_bash(self, source: str) -> str:
        """
        If the source is a bash cell, converts it to a temporary script and returns
        the command to execute it. Otherwise, returns the original source.
        """
        if not source.startswith("%%bash\n"):
            return source

        # Remove the "%%bash\n" prefix
        bash_content = source[7:]

        # Create a temporary file with the bash script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(bash_content)
            temp_path = f.name

        # Make the script executable
        os.chmod(temp_path, 0o755)

        # Execute the script and clean up
        source = f"!bash {temp_path}"
        jupyter_notebook_logger.debug(f"Converted bash cell to: {source}")

        return source


async def test_bash_script_handler():
    handler = BashScriptHandler()
    
    # Test non-bash source remains unchanged
    python_source = "print('hello')"
    assert handler.convert_if_bash(python_source) == python_source
    
    # Test bash source is converted
    bash_source = "%%bash\necho 'hello'"
    converted = handler.convert_if_bash(bash_source)
    assert converted.startswith("!bash ")
    assert converted.endswith(".sh")
    
    # Test the created script is executable and contains the correct content
    script_path = converted[6:]  # Remove "!bash " prefix
    with open(script_path, 'r') as f:
        content = f.read()
        assert content == "echo 'hello'"
    
    # Test file permissions
    assert os.access(script_path, os.X_OK)
    
    # Clean up
    os.unlink(script_path)
