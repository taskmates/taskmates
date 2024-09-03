import os
import signal
import subprocess
import textwrap

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture
def cli_runner(tmp_path):
    def run_cli_command(args):
        cmd = ["taskmates"] + args
        taskmates_home = tmp_path / ".taskmates"
        env = os.environ.copy()
        env["TASKMATES_HOME"] = str(taskmates_home)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(tmp_path),
            env=env
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode

    return run_cli_command


def test_chat_completion(cli_runner, tmp_path):
    args = ["complete", "--model=quote", "Short answer. 1+1="]
    stdout, stderr, returncode = cli_runner(args)

    expected_response = textwrap.dedent("""
    > Short answer. 1+1=
    > 
    > """)

    assert returncode == 0
    assert stderr == ""
    assert stdout == expected_response


def test_chat_completion_with_mention(cli_runner, tmp_path):
    taskmates_home = tmp_path / ".taskmates"
    (taskmates_home / "taskmates").mkdir(parents=True)
    (taskmates_home / "taskmates" / "jeff.md").write_text("You're a helpful assistant\n")

    args = ["complete", "--model=quote", "Hey @jeff short answer. 1+1="]
    stdout, stderr, returncode = cli_runner(args)

    expected_response = textwrap.dedent("""
    > Hey @jeff short answer. 1+1=
    > 
    > """)

    assert returncode == 0
    assert not stderr
    assert stdout == expected_response


def test_tool_completion(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    How much is 1 + 1?

    **assistant>**

    How much is 1 + 1?

    ###### Steps

    - Run Shell Command [1] `{"cmd":"echo $((1 + 1))"}`

    """)

    args = ["complete", "--model=quote", markdown_chat]
    stdout, stderr, returncode = cli_runner(args)

    expected_response = textwrap.dedent("""\
    ###### Execution: Run Shell Command [1]

    <pre class='output' style='display:none'>
    2

    Exit Code: 0
    </pre>
    -[x] Done

    """)

    assert returncode == 0
    assert not stderr
    assert stdout == expected_response


def test_code_cell_completion(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    print(1 + 1)
    
    **assistant>**
    
    print(1 + 1)
    
    ```python .eval
    print(1 + 1)
    ```
    
    """)

    args = ["complete", "--model=quote", markdown_chat]
    stdout, stderr, returncode = cli_runner(args)

    expected_completion = textwrap.dedent("""\
    ###### Cell Output: stdout [cell_0]

    <pre>
    2
    </pre>

    """)

    assert returncode == 0
    # assert not stderr
    assert stdout == expected_completion


def test_error_completion(cli_runner, tmp_path):
    args = ["complete", "--model=non-existent-model", "REQUEST"]
    stdout, stderr, returncode = cli_runner(args)

    assert "error" in stdout.lower() or "error" in stderr.lower()


@pytest.mark.timeout(10)
def test_interrupt_tool(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    How much is 1 + 1?

    **assistant>**

    How much is 1 + 1?

    ###### Steps

    - Run Shell Command [1] `{"cmd":"echo 2; sleep 5; echo fail"}`

    """)

    args = ["complete", "--model=quote", markdown_chat]
    process = subprocess.Popen(
        ["taskmates"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(tmp_path)
    )

    output = ""
    while "2" not in output:
        output += process.stdout.readline()

    process.send_signal(signal.SIGINT)

    stdout, stderr = process.communicate()
    output += stdout

    expected_response = textwrap.dedent("""\
    ###### Execution: Run Shell Command [1]

    <pre class='output' style='display:none'>
    2
    --- INTERRUPT ---
    
    Exit Code: -2
    </pre>
    -[x] Done

    """)

    assert process.returncode == 0
    assert output == expected_response


@pytest.mark.timeout(10)
def test_kill_tool(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    Run a command that ignores SIGINT
    
    **assistant>**
    
    Certainly! I'll run a command that ignores the SIGINT signal.
    
    ###### Steps
    
    - Run Shell Command [1] `{"cmd":"trap '' INT; echo Starting; sleep 5; echo fail"}`
    
    """)

    expected_response = textwrap.dedent("""\
    ###### Execution: Run Shell Command [1]

    <pre class='output' style='display:none'>
    Starting
    --- KILL ---

    Exit Code: -9
    </pre>
    -[x] Done

    """)

    args = ["complete", "--model=quote", markdown_chat]
    process = subprocess.Popen(
        ["taskmates"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(tmp_path)
    )

    output = ""
    while "Starting" not in output:
        output += process.stdout.readline()

    process.send_signal(signal.SIGTERM)

    stdout, stderr = process.communicate()
    output += stdout

    assert process.returncode == 0
    assert output == expected_response


def test_code_cell_no_output(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    print(1 + 1)

    **assistant>**

    print(1 + 1)

    ```python .eval
    # This code cell doesn't produce any output
    ```

    """)

    args = ["complete", "--model=quote", markdown_chat]
    stdout, stderr, returncode = cli_runner(args)

    expected_completion = textwrap.dedent("""\
    ###### Cell Output: stdout [cell_0]

    Done

    """)

    assert returncode == 0
    # assert not stderr
    assert stdout == expected_completion


@pytest.mark.timeout(10)
def test_kill_code_cell(cli_runner, tmp_path):
    markdown_chat = textwrap.dedent("""
    Run a command that ignores SIGINT in a code cell
    
    **assistant>**
    
    Certainly! I'll run a command that ignores the SIGINT signal in a code cell.
    
    ```python .eval
    !trap '' INT; echo Starting; sleep 5; echo fail
    ```
    
    """)

    args = ["complete", "--model=quote", markdown_chat]
    process = subprocess.Popen(
        ["taskmates"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(tmp_path)
    )

    output = ""
    while "Starting" not in output:
        output += process.stdout.readline()

    process.send_signal(signal.SIGKILL)

    stdout, stderr = process.communicate()
    output += stdout

    expected_response = textwrap.dedent("""\
    ###### Cell Output: stdout [cell_0]

    <pre>
    Starting
    """)

    assert output == expected_response
    assert process.returncode == -9


def test_chat_completion_from_stdin(tmp_path):
    taskmates_home = tmp_path / ".taskmates"
    env = os.environ.copy()
    env["TASKMATES_HOME"] = str(taskmates_home)

    cmd = ["taskmates", "complete", "--model=quote"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(tmp_path),
        env=env
    )

    stdin_input = "Short answer. 1+1="
    stdout, stderr = process.communicate(input=stdin_input)

    expected_response = textwrap.dedent("""
    > Short answer. 1+1=
    > 
    > """)

    assert process.returncode == 0
    assert not stderr
    assert stdout == expected_response
