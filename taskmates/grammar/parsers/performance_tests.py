import textwrap
import timeit

import pyparsing as pp
import pytest

from taskmates.grammar.parsers.markdown_chat_parser import markdown_chat_parser
from taskmates.lib.openai_.count_tokens import count_tokens

pytestmark = pytest.mark.slow


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance():
    pp.enable_all_warnings()

    partial = textwrap.dedent("""\
        **user>** This is a messag with multiple lines.
        This is a messag with multiple lines.
        This is a messag with multiple lines.
        
        **assistant>** This is a response.
        
        **user {"name": "john"}>** This is a message with attributes.
        
        **assistant>** This is a response from the assistant.
        
        **john>** This is another message from john.
        
        **assistant>** This is a message with tool calls.
        
        ###### Steps
        
        - Run Shell Command [1] `{"cmd":"echo hello"}`
        - Run Shell Command [2] `{"cmd":"echo world"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre class='output' style='display:none'>
        hello
        
        Exit Code: 0
        </pre>
        
        -[x] Done
        
        ###### Execution: Run Shell Command [2]
        
        <pre class='output' style='display:none'>
        world
        
        Exit Code: 0
        </pre>
        
        -[x] Done
        
        **user>** This is a message with code cells
        
        ```python .eval
        print("hello")
        ```
        
        ```python .eval
        print("world")
        ```
        
        ###### Cell Output: stdout [cell_0]
        
        <pre>
        hello
        </pre>
        
        ###### Cell Output: stdout [cell_1]
        
        <pre>
        world
        </pre>
        """)

    markdown_chat_parser().parseString(generate_input_string(partial))


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_single_lines():
    partial = textwrap.dedent("""\
    **user>** This is a test message
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Single lines message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_long_lines():
    partial = textwrap.dedent("""\
    **user>** This is a test message This is a test message This is a test message This is a test message This is a test message This is a test message This is a test message
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Long lines message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_single_lines_plus_new_line():
    partial = textwrap.dedent("""\
    **user>** This is a test message
    
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Single lines plus new line message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_line_break_plus_message():
    partial = textwrap.dedent("""\
    **user>**
    This is a test message
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Line break plus message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_multiple_lines():
    partial = textwrap.dedent("""\
    **user>** This is a test message
    with multiple lines.
    It should be parsed quickly.
    
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Multiple lines message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_tool_calls():
    partial = textwrap.dedent("""\
    **assistant>** Here's an example of tool calls:

    ###### Steps

    - Run Shell Command [1] `{"cmd":"echo hello"}`
    - Run Shell Command [2] `{"cmd":"echo world"}`

    ###### Execution: Run Shell Command [1]

    <pre class='output' style='display:none'>
    hello

    Exit Code: 0
    </pre>

    -[x] Done

    ###### Execution: Run Shell Command [2]

    <pre class='output' style='display:none'>
    world

    Exit Code: 0
    </pre>

    -[x] Done
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Tool calls message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(5)
@pytest.mark.xdist_group(name="performance")
def test_performance_code_cells():
    partial = textwrap.dedent("""\
    **assistant>** Here's an example of how to print "Hello, World!" in Python:

    ```python
    print("Hello, World!")
    ```

    And here's how you would do it in JavaScript:

    ```javascript
    console.log("Hello, World!");
    ```
    """)

    input_string = generate_input_string(partial)
    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(input_string), number=1)
    print(f"Code cells message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 0.6, f"Parsing took too long: {execution_time:.4f} seconds"


def generate_input_string(base_string: str, target_token_count: int = 10_000) -> str:
    result = ""
    current_token_count = 0

    while current_token_count < target_token_count:
        result += base_string
        current_token_count = count_tokens(result)

    return result
