import argparse
import asyncio
import logging

import taskmates
from taskmates import env
from taskmates.cli.commands.complete import CompleteCommand
from taskmates.cli.commands.server import ServerCommand
from taskmates.signal_config import SignalConfig, SignalMethod

env.bootstrap()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Taskmates CLI')
    parser.add_argument('--version', action='version', version=f'Taskmates {taskmates.__version__}')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--input-method', choices=['default', 'websocket'], default='default',
                        help='Select input method for control signals')
    parser.add_argument('--output-method', choices=['default', 'websocket'], default='default',
                        help='Select output method for response signals')
    parser.add_argument('--websocket-url', default='ws://localhost:8765',
                        help='WebSocket URL for websocket method')
    subparsers = parser.add_subparsers(dest='command')

    commands = {
        'complete': CompleteCommand(),
        'server': ServerCommand(),
    }

    for name, command in commands.items():
        command_parser = subparsers.add_parser(name, help=f'{name.capitalize()} command')
        command.add_arguments(command_parser)

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    signal_config = SignalConfig(
        input_method=SignalMethod(args.input_method),
        output_method=SignalMethod(args.output_method),
        websocket_url=args.websocket_url
    )

    if args.command in commands:
        logger.info(f"Executing command: {args.command}")
        try:
            asyncio.run(commands[args.command].execute(args, signal_config))
        except Exception as e:
            logger.error(f"Error executing command {args.command}: {str(e)}", exc_info=True)
    else:
        logger.warning("No valid command provided")
        parser.print_help()

if __name__ == "__main__":
    main()
