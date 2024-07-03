import argparse
from datetime import datetime
import os
from taskmates.cli.commands.base import Command
from taskmates.cli.lib.screenshot import take_screenshot

class ScreenshotCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument('--output', help='Output file path for the screenshot')

    async def execute(self, args: argparse.Namespace):
        output_path = args.output
        if not output_path:
            # Generate a filename with a timestamp if no output path is provided
            timestamp = datetime.now().strftime("%Y-%m-%d at %H.%M.%S")
            output_path = f'/tmp/taskmates/Screenshot {timestamp}.png'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        take_screenshot(output_path)
        print("!" + f"[{output_path}]({output_path})")
