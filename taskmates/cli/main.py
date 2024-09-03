import argparse
import asyncio
import os

import taskmates
from taskmates.cli.commands.complete import CompleteCommand
from taskmates.cli.commands.parse import ParseCommand
from taskmates.cli.commands.screenshot import ScreenshotCommand
from taskmates.cli.commands.server import ServerCommand
from taskmates.cli.commands.tools import ToolsCommand
from taskmates.logging import logger
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


def main():
    TASKMATES_RUNTIME.get().initialize()

    parser = argparse.ArgumentParser(description='Taskmates CLI')
    parser.add_argument('--version', action='version', version=f'Taskmates {taskmates.__version__}')
    subparsers = parser.add_subparsers(dest='command')

    commands = {
        'screenshot': ScreenshotCommand(),
        'parse': ParseCommand(),
        'complete': CompleteCommand(),
        'server': ServerCommand(),
        'tools': ToolsCommand(),
    }

    for name, command in commands.items():
        command_parser = subparsers.add_parser(name, help=f'{name.capitalize()} command')
        command.add_arguments(command_parser)

    args = parser.parse_args()

    if args.command in commands:
        logger.info(f"Executing command: {args.command}")
        try:
            asyncio.run(commands[args.command].execute(args))
        except Exception as e:
            if os.environ.get("TASKMATES_ENV", "production") == "production":
                logger.error(f"Error executing command {args.command}: {str(e)}", exc_info=True)
            else:
                raise e
    else:
        logger.warning("No valid command provided")
        parser.print_help()


if __name__ == "__main__":
    main()
