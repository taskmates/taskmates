import textwrap
import timeit

import pyparsing as pp
import pytest
from pyparsing import LineStart

from taskmates.grammar.parsers.front_matter_parser import front_matter_parser
from taskmates.grammar.parsers.messages_parser import messages_parser


def markdown_chat_parser():
    comments = pp.Suppress(LineStart() + pp.Literal("[//]: #") + pp.restOfLine)
    return (pp.Opt(front_matter_parser()) + messages_parser() + pp.string_end).ignore(comments)


def test_markdown_with_tool_execution():
    input = textwrap.dedent("""\
        **assistant** Here is a message.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user** Here is another message.
        """)

    result = markdown_chat_parser().parseString(input)
    messages = [m.as_dict() for m in result.messages]
    assert messages == [
        {
            'content': 'Here is a message.\n\n',
            'name': 'assistant',
            'tool_calls': [
                {
                    'function': {
                        'arguments': {'cmd': 'cd /tmp'},
                        'name': 'run_shell_command'
                    },
                    'id': '1',
                    'type': 'function'
                }
            ]
        },
        {'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n',
         'name': 'run_shell_command',
         'role': 'tool',
         'tool_call_id': '1'},
        {
            'content': 'Here is another message.\n',
            'name': 'user'
        }
    ]


def test_markdown_with_code_cell_execution():
    input = textwrap.dedent("""\
        print(1 + 1)
        
        **assistant**
        
        print(1 + 1)
        
        ```python .eval
        print(1 + 1)
        ```

        ###### Cell Output: stdout [cell_0]
    
        <pre>
        2
        </pre>
    
        **assistant** 
        
        1 + 1 equals 2.

        """)

    result = markdown_chat_parser().parseString(input)
    messages = [m.as_dict() for m in result.messages]
    assert messages == [
        {
            'content': 'print(1 + 1)\n\n', 'name': 'user'
        },
        {
            'content': '\n'
                       'print(1 + 1)\n'
                       '\n'
                       '```python .eval\n'
                       'print(1 + 1)\n'
                       '```\n'
                       '\n'
            ,
            'name': 'assistant'
        },
        {'code_cell_id': 'cell_0',
         'content': '\n<pre>\n2\n</pre>\n\n',
         'role': 'cell_output',
         'name': 'stdout'},
        {
            'content': '\n\n1 + 1 equals 2.\n\n',
            'name': 'assistant'
        }]


@pytest.mark.timeout(2)
def test_performance():
    pp.enable_all_warnings()

    partial = textwrap.dedent("""\
        **user** This is a messag with multiple lines.
        This is a messag with multiple lines.
        This is a messag with multiple lines.
        
        **assistant** This is a response.
        
        **user {"name": "john"}** This is a message with attributes.
        
        **assistant** This is a response from the assistant.
        
        **john** This is another message from john.
        
        **assistant** This is a message with tool calls.
        
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
        
        **user** This is a message with code cells
        
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

    input = partial * 50

    markdown_chat_parser().parseString(input)


@pytest.mark.timeout(2)
def test_performance_multiple_lines():
    message = textwrap.dedent("""\
    **user** This is a test message
    with multiple lines.
    It should be parsed quickly.
    
    """) * 50

    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(message), number=1)
    print(f"Multiple lines message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 1, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(2)
def test_performance_tool_calls():
    message = textwrap.dedent("""\
    **assistant** Here's an example of tool calls:

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

    -[x] Done""") * 50

    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(message), number=1)
    print(f"Tool calls message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 1, f"Parsing took too long: {execution_time:.4f} seconds"


@pytest.mark.timeout(2)
def test_performance_code_cells():
    message = textwrap.dedent("""\
    **assistant** Here's an example of how to print "Hello, World!" in Python:

    ```python
    print("Hello, World!")
    ```

    And here's how you would do it in JavaScript:

    ```javascript
    console.log("Hello, World!");
    ```""") * 50

    execution_time = timeit.timeit(lambda: markdown_chat_parser().parseString(message), number=1)
    print(f"Code cells message parsing time: {execution_time:.4f} seconds")
    assert execution_time < 1, f"Parsing took too long: {execution_time:.4f} seconds"
