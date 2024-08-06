import base64
import hashlib
import json

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
    def escape_angle_brackets(text):
        return text.replace('<', '&lt;').replace('>', '&gt;')

    @staticmethod
    def format_code_cell_output(result, is_preformatted):
        formatted = result if isinstance(result, str) else json.dumps(result)
        formatted = strip_ansi(formatted)
        if is_preformatted:
            formatted = CodeExecution.escape_angle_brackets(formatted)
        return formatted

    @staticmethod
    def generate_code_cell_id(code_cell_content):
        digest = hashlib.sha256(code_cell_content.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
