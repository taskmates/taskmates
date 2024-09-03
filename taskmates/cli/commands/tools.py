import argparse
import json

from typeguard import typechecked

from taskmates.cli.commands.base import Command
from taskmates.core.tools_registry import tools_registry
from taskmates.lib.inspect_.get_qualified_function_name import get_qualified_function_name
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


class ToolsCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(dest='subcommand')

        # Subparser for the 'list' command
        list_parser = subparsers.add_parser('list', help='List all functions as JSON')

        # Subparser for the 'invoke' command
        invoke_parser = subparsers.add_parser('invoke', help='Invoke a function by name with arguments')
        invoke_parser.add_argument('--name', required=True, help='Name of the function to invoke')
        invoke_parser.add_argument('--arguments', required=True,
                                   help='JSON string of arguments to pass to the function')

    async def execute(self, args: argparse.Namespace):
        TASKMATES_RUNTIME.get().initialize()

        if args.subcommand == 'list':
            result = await cli_list_functions()
            print(result)
        elif args.subcommand == 'invoke':
            arguments = json.loads(args.arguments)
            await cli_invoke_function(args.name, arguments)
        else:
            print("Invalid subcommand. Use 'list' or 'invoke'.")


async def cli_list_functions():
    # TODO return full command line
    # root_path / "bin/function_registry" "invoke"

    function_full_names = {k: get_qualified_function_name(v) for k, v in tools_registry.items()}
    return json.dumps(function_full_names, indent=2, ensure_ascii=False)


@typechecked
async def cli_invoke_function(name: str, arguments: dict):
    if name not in tools_registry:
        raise ValueError(f"Function '{name}' not found in the constructors.")
    func = tools_registry[name]

    args = arguments
    if not isinstance(args, dict):
        raise ValueError("Arguments must be a JSON object.")
    # print(f"FunctionRegistry: Invoking function '{name}' with arguments: {args}")

    result = await func(**args)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
