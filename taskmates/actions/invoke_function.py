import asyncio
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from taskmates.lib.restore_stdout_and_stderr import restore_stdout_and_stderr
from taskmates.signals.signals import Signals


# TODO: review this and the duplication with run_shell_command
async def stream_output(stream_name, stream, signals: Signals):
    while True:
        line = stream.readline()
        if not line:
            break
        with restore_stdout_and_stderr():
            await signals.output.response.send_async(line)


async def invoke_function(function, kwargs, signals: Signals):
    stdout_stream = StringIO()
    stderr_stream = StringIO()

    async def run_function():
        with redirect_stdout(stdout_stream), redirect_stderr(stderr_stream):
            # print(f"Taskmates: Invoking function '{name}' with arguments: {kwargs}")
            if asyncio.iscoroutinefunction(function):
                return await function(**kwargs)
            else:
                return function(**kwargs)

    stdout_task = asyncio.create_task(stream_output("stdout", stdout_stream, signals))
    stderr_task = asyncio.create_task(stream_output("stderr", stderr_stream, signals))

    result = await run_function()

    # stdout_stream.seek(0)
    # stderr_stream.seek(0)

    await stdout_task
    await stderr_task

    return result
