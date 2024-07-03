import argparse
import asyncio
import taskmates
from taskmates.cli.commands.screenshot import ScreenshotCommand
from taskmates.cli.commands.parse import ParseCommand
from taskmates.cli.commands.complete import CompleteCommand

def main():
    parser = argparse.ArgumentParser(description='Taskmates CLI')
    parser.add_argument('--version', action='version', version=f'Taskmates {taskmates.__version__}')
    subparsers = parser.add_subparsers(dest='command')

    commands = {
        'screenshot': ScreenshotCommand(),
        'parse': ParseCommand(),
        'complete': CompleteCommand(),
    }

    for command_name, command_instance in commands.items():
        command_parser = subparsers.add_parser(command_name, help=f'{command_name.capitalize()} command')
        command_instance.add_arguments(command_parser)

    args = parser.parse_args()
    
    if args.command in commands:
        asyncio.run(commands[args.command].execute(args))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
