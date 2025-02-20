import base64
import hashlib
import json
import re

from nbconvert.filters.ansi import strip_ansi


class CodeExecution:
    @staticmethod
    def is_raw_output(function_title):
        return function_title in ["Visit Page", "Dump Screenshot"]

    @staticmethod
    def format_tool_output_header(function_title, tool_call_id):
        execution_header = f"###### Execution: {function_title} [{tool_call_id}]\n\n"
        pre_tag = "<pre class='output' style='display:none'>\n"

        if not CodeExecution.is_raw_output(function_title):
            return execution_header + pre_tag
        else:
            return execution_header

    @staticmethod
    def format_code_cell_output_header(output_title, cell_id, is_preformatted):
        formatted = f"###### Cell Output: {output_title} [{cell_id}]\n\n"
        if is_preformatted:
            formatted += "<pre>\n"

        return formatted

    @staticmethod
    def format_tool_output_footer(function_title):
        done_message = "\n-[x] Done\n\n"
        pre_close_tag = "\n</pre>"

        if not CodeExecution.is_raw_output(function_title):
            return pre_close_tag + done_message
        else:
            return done_message

    @staticmethod
    def format_code_cell_output_footer(was_preformatted, was_empty):
        if was_empty:
            return "Done\n\n"

        execution_footer = "</pre>\n\n" if was_preformatted else "\n"
        return execution_footer

    @staticmethod
    def escape_pre_output(text):
        return text.replace('<', '&lt;').replace('>', '&gt;')

    @staticmethod
    def strip_control_chars(text):
        # First use strip_ansi to remove ANSI escape sequences
        text = strip_ansi(text)
        
        # Remove carriage returns
        text = text.replace("\r", "")
        
        # Remove other control characters except newlines and tabs
        # This pattern matches any character that is a control character (ASCII 0-31)
        # except for newline (\n, ASCII 10) and tab (\t, ASCII 9)
        text = re.sub(r'[\x00-\x08\x0B-\x1F\x7F]', '', text)
        
        return text

    @staticmethod
    def format_code_cell_output(result, is_preformatted):
        formatted = result if isinstance(result, str) else json.dumps(result)
        formatted = CodeExecution.strip_control_chars(formatted)
        if is_preformatted:
            formatted = CodeExecution.escape_pre_output(formatted)
        return formatted

    @staticmethod
    def generate_code_cell_id(code_cell_content):
        digest = hashlib.sha256(code_cell_content.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


def test_strip_control_chars():
    # Test with various control characters
    input_text = "Hello\x1B[31m World\x1B[0m\r\n\x00\x01\x02\tTest\n"
    expected = "Hello World\n\tTest\n"
    assert CodeExecution.strip_control_chars(input_text) == expected

    # Test with just normal text
    input_text = "Hello World"
    assert CodeExecution.strip_control_chars(input_text) == "Hello World"

    # Test with multiple carriage returns and newlines
    input_text = "Hello\r\n\r\nWorld"
    assert CodeExecution.strip_control_chars(input_text) == "Hello\n\nWorld"

    # Test with escape sequences
    input_text = "Hello\x1B[31mWorld\x1B[0m"
    assert CodeExecution.strip_control_chars(input_text) == "HelloWorld"

    # Test with null bytes and other control characters
    input_text = "Hello\x00\x01\x02World"
    assert CodeExecution.strip_control_chars(input_text) == "HelloWorld"

    # Test with tabs (should preserve them)
    input_text = "Hello\tWorld"
    assert CodeExecution.strip_control_chars(input_text) == "Hello\tWorld"
