import argparse
import asyncio
import logging

import taskmates
from taskmates import env
from taskmates.cli.commands.complete import CompleteCommand
from taskmates.cli.commands.parse import ParseCommand
from taskmates.cli.commands.screenshot import ScreenshotCommand
from taskmates.cli.commands.server import ServerCommand

env.bootstrap()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Taskmates CLI')
    parser.add_argument('--version', action='version', version=f'Taskmates {taskmates.__version__}')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    subparsers = parser.add_subparsers(dest='command')

    commands = {
        'screenshot': ScreenshotCommand(),
        'parse': ParseCommand(),
        'complete': CompleteCommand(),
        'server': ServerCommand(),
    }

    for command_name, command_instance in commands.items():
        command_parser = subparsers.add_parser(command_name, help=f'{command_name.capitalize()} command')
        command_instance.add_arguments(command_parser)

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if args.command in commands:
        logger.info(f"Executing command: {args.command}")
        try:
            asyncio.run(commands[args.command].execute(args))
        except Exception as e:
            logger.error(f"Error executing command {args.command}: {str(e)}", exc_info=True)
    else:
        logger.warning("No valid command provided")
        parser.print_help()


if __name__ == "__main__":
    main()
