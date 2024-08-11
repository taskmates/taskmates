import asyncio
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from taskmates.config.completion_context import CompletionContext
from taskmates.lib.context_.temp_cwd import temp_cwd
from taskmates.lib.context_.temp_environ import temp_environ
from taskmates.lib.restore_stdout_and_stderr import restore_stdout_and_stderr
from taskmates.signals.signals import Signals


# TODO: review this and the duplication with run_shell_command
async def stream_output(stream_name, stream, signals: Signals):
    while True:
        line = stream.readline()
        if not line:
            break
        with restore_stdout_and_stderr():
            await signals.response.response.send_async(line)


async def invoke_function(function, arguments, context: CompletionContext, signals: Signals):
    stdout_stream = StringIO()
    stderr_stream = StringIO()

    async def run_function():
        with redirect_stdout(stdout_stream), redirect_stderr(stderr_stream):
            # print(f"Taskmates: Invoking function '{name}' with arguments: {kwargs}")

            with temp_environ(context['env']), temp_cwd(context['cwd']):
                if asyncio.iscoroutinefunction(function):
                    return await function(**arguments)
                else:
                    return function(**arguments)

    stdout_task = asyncio.create_task(stream_output("stdout", stdout_stream, signals))
    stderr_task = asyncio.create_task(stream_output("stderr", stderr_stream, signals))

    result = await run_function()

    # stdout_stream.seek(0)
    # stderr_stream.seek(0)

    await stdout_task
    await stderr_task

    return result
