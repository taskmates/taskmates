import hashlib

from taskmates.lib.str_.to_snake_case import to_snake_case


def generate_tool_call_id(function_name, index, arguments):
    # Convert the function name to snake_case
    function_name_snake_case = to_snake_case(function_name)

    # Concatenate the function name, index, and arguments
    id_content = f"{function_name_snake_case}_{index}_{arguments}"

    # Generate a digest of the id_content
    digest = hashlib.sha256(id_content.encode('utf-8')).hexdigest()[:24]

    return f"call_{digest}"
