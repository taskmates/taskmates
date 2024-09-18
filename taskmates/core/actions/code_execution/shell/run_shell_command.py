import asyncio
import os
import platform
import signal
import subprocess

import pytest
import sys

from taskmates.core.signals.signals_context import SignalsContext
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.restore_stdout_and_stderr import restore_stdout_and_stderr


# TODO: review this and the duplication with invoke_function
async def stream_output(fd, stream, signals):
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, stream.readline)
        if not line:
            break
        with restore_stdout_and_stderr():
            await signals.response.response.send_async(line)


async def run_shell_command(cmd: str) -> str:
    """
    Runs a shell command on the user's machine. Be mindful with large outputs. Make sure to add flags like --quiet or --silent or | tail -n 10 to limit the output.

    :param cmd: the command
    :return: the output of the command
    """

    signals: SignalsContext = EXECUTION_CONTEXT.get().signals

    if platform.system() == "Windows":
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setpgrp
        )

    async def interrupt_handler(sender):
        if platform.system() == "Windows":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        await signals.lifecycle.interrupted.send_async(None)

    async def kill_handler(sender):
        if platform.system() == "Windows":
            process.kill()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        await signals.lifecycle.killed.send_async(None)

    with signals.control.interrupt.connected_to(interrupt_handler), \
            signals.control.kill.connected_to(kill_handler):
        stdout_task = asyncio.create_task(stream_output(sys.stdout, process.stdout, signals))
        stderr_task = asyncio.create_task(stream_output(sys.stderr, process.stderr, signals))

        await asyncio.wait([stdout_task, stderr_task])

        exit_code = await asyncio.get_event_loop().run_in_executor(None, process.wait)
        return f'\nExit Code: {exit_code}'


@pytest.mark.asyncio
async def test_run_shell_command(capsys):
    signals = EXECUTION_CONTEXT.get().signals
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.response.connect(capture_chunk)

    if platform.system() == "Windows":
        cmd = "echo Hello, World!"
    else:
        cmd = "echo 'Hello, World!'"

    returncode = await run_shell_command(cmd)

    assert returncode == '\nExit Code: 0'
    assert "".join(chunks).strip() == "Hello, World!"


@pytest.mark.asyncio
async def test_run_shell_command_interrupt(capsys):
    signals = EXECUTION_CONTEXT.get().signals
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.response.connect(capture_chunk)

    async def send_interrupt():
        while len(chunks) < 5:
            await asyncio.sleep(0.1)
        await signals.control.interrupt.send_async(None)

    interrupt_task = asyncio.create_task(send_interrupt())

    if platform.system() == "Windows":
        cmd = "for /L %i in (1,1,10) do @(echo %i & timeout /t 1 > nul)"
    else:
        cmd = "seq 5; sleep 1; seq 6 10"

    returncode = await run_shell_command(cmd)

    await interrupt_task

    if platform.system() == "Windows":
        assert returncode == '\nExit Code: 1'
    else:
        assert returncode == f'\nExit Code: {-signal.SIGINT.value}'
    assert "".join(chunks).strip() == "1\n2\n3\n4\n5"


@pytest.mark.asyncio
async def test_run_shell_command_kill(capsys):
    signals = EXECUTION_CONTEXT.get().signals
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.response.connect(capture_chunk)

    async def send_kill():
        while len(chunks) < 3:
            await asyncio.sleep(0.1)
        await signals.control.kill.send_async(None)

    kill_task = asyncio.create_task(send_kill())

    if platform.system() == "Windows":
        cmd = "for /L %i in (1,1,5) do @(echo %i & timeout /t 1 > nul) & timeout /t 1 > nul & for /L %i in (6,1,10) do @echo %i"
    else:
        cmd = "seq 5; sleep 1; seq 6 10"

    return_code = await run_shell_command(cmd)

    await kill_task

    if platform.system() == "Windows":
        assert return_code == '\nExit Code: 1'
    else:
        assert return_code == f'\nExit Code: {-signal.SIGKILL.value}'

    assert "".join(chunks).strip() == "1\n2\n3\n4\n5"
