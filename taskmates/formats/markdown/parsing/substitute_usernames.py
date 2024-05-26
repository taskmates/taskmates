import re
import textwrap

from typeguard import typechecked

from taskmates.lib.str_.to_snake_case import to_snake_case


@typechecked
def substitute_usernames(content: str):
    content = re.sub(r'^\*\*([a-z_0-9]+)\*\*:?', r'**user {"name": "\1"}**', content, flags=re.MULTILINE)

    content = re.sub(r'^###### Execution: (.*) \[(\d+)]', lambda
        match: f'**tool {{"name": "{to_snake_case(match.group(1))}", "tool_call_id": "{match.group(2)}"}}**',
                     content,
                     flags=re.MULTILINE)

    content = re.sub(r'^(###### Cell Output: .*)$', lambda
        match: f'**user**\n{match.group(1)}',
                     content,
                     flags=re.MULTILINE)

    # else:
    # TODO: skip if claude

    return content


def test_substitute_usernames():
    input_content = """\
    **steve**
    
    Hi all
    
    **john**: hello
    
    **alice** hi **john**
    """
    expected_output = """\
    **user {"name": "steve"}**
    
    Hi all
    
    **user {"name": "john"}** hello
    
    **user {"name": "alice"}** hi **john**
    """

    assert substitute_usernames(textwrap.dedent(input_content)) == textwrap.dedent(expected_output)


def test_substitute_usernames_on_tools():
    input_content = """\
        **user** @shell cd into /tmp and list the files
        
        **shell** 
        
        ###### Steps
        
        - Run Shell Command [1] `{"cmd":"cd /tmp && ls"}`
        
        ###### Execution: Run Shell Command [1] 
        
        <pre>
        mysql.sock
        
        Exit Code: 0
        </pre>
        
        **shell** I successfully changed the directory to `/tmp` and listed the files. 
    """
    expected_output = """\
        **user {"name": "user"}** @shell cd into /tmp and list the files
        
        **user {"name": "shell"}** 
        
        ###### Steps
        
        - Run Shell Command [1] `{"cmd":"cd /tmp && ls"}`
        
        **tool {"name": "run_shell_command", "tool_call_id": "1"}** 
        
        <pre>
        mysql.sock
        
        Exit Code: 0
        </pre>
        
        **user {"name": "shell"}** I successfully changed the directory to `/tmp` and listed the files. 
    """

    assert substitute_usernames(textwrap.dedent(input_content)) == textwrap.dedent(expected_output)
