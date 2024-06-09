import argparse
import taskmates
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime

from taskmates.actions.invoke_function import invoke_function
from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.signals import Signals


async def take_screenshot(output_path):
    # Use the screencapture command to take a screenshot
    subprocess.run(["screencapture", "-i", output_path])


def main():
    parser = argparse.ArgumentParser(description='Taskmates CLI')
    parser.add_argument('--version', action='version', version=f'Taskmates {taskmates.__version__}')
    subparsers = parser.add_subparsers(dest='command')

    # Subparser for the 'invoke' command
    invoke_parser = subparsers.add_parser('invoke', help='Invoke a function by name with arguments')
    invoke_parser.add_argument('--name', required=True, help='Name of the function to invoke')
    invoke_parser.add_argument('--arguments', required=True, help='JSON string of arguments to pass to the function')

    # Subparser for the 'screenshot' command
    screenshot_parser = subparsers.add_parser('screenshot', help='Take a screenshot and save it')
    screenshot_parser.add_argument('--output', help='Output file path for the screenshot')
    # Subparser for the 'parse' command
    parse_parser = subparsers.add_parser('parse',
                                         help='Parse a markdown chat file from stdin and print the extracted chat as JSON')

    # Parse the arguments
    args = parser.parse_args()
    asyncio.run(async_main(args, parser))


async def async_main(args, parser):
    if args.command == 'invoke':
        try:
            result = await invoke_function(args.name, args.arguments, Signals())
            if result is not None:
                if isinstance(result, str):
                    print(result)
                else:
                    print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            raise e
    elif args.command == 'screenshot':
        output_path = args.output
        if not output_path:
            # Generate a filename with a timestamp if no output path is provided
            timestamp = datetime.now().strftime("%Y-%m-%d at %H.%M.%S")
            output_path = f'/tmp/taskmates/Screenshot {timestamp}.png'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        await take_screenshot(output_path)
        print("!" + f"[{output_path}]({output_path})")
    elif args.command == 'parse':
        markdown_chat = "".join(sys.stdin.readlines())
        result = await parse_markdown_chat(markdown_chat, None)
        print(json.dumps(result, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
