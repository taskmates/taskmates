import argparse
import asyncio
import inspect
import json

from typeguard import typechecked

from taskmates.assistances.code_execution.shell_.run_shell_command import run_shell_command
from tools.chroma_.chromadb_search import chromadb_search
from tools.dalle_.convert_to_svg import convert_to_svg
from tools.dalle_.generate_images import generate_images
from tools.evaluation_.report_evaluation import report_evaluation
from tools.filesystem_.read_file import read_file
from tools.filesystem_.write_file import write_file
from tools.google_.google_search import google_search
from tools.jira_.jira_ import create_issue, add_comment, update_status, search_issues, delete_issues, dump_context, \
    read_issue

function_registry = {}


def initialize_function_registry(function_registry):
    # return status
    function_registry["report_evaluation"] = report_evaluation

    # execution
    function_registry["run_shell_command"] = run_shell_command

    # file system
    function_registry["read_file"] = read_file
    function_registry["write_file"] = write_file

    # browser
    function_registry["google_search"] = google_search

    # rag
    function_registry["chromadb_search"] = chromadb_search

    # images
    function_registry["generate_images"] = generate_images
    function_registry["convert_to_svg"] = convert_to_svg

    # jira
    function_registry["create_issue"] = create_issue
    function_registry["read_issue"] = read_issue
    function_registry["add_comment"] = add_comment
    function_registry["update_status"] = update_status
    function_registry["search_issues"] = search_issues
    function_registry["delete_issues"] = delete_issues
    function_registry["dump_context"] = dump_context


initialize_function_registry(function_registry)


def get_fullname(obj):
    module = inspect.getmodule(obj)
    if module:
        return module.__name__ + '.' + obj.__qualname__
    else:
        return obj.__qualname__


async def list_functions():
    # TODO return full command line
    # root_path / "bin/function_registry" "invoke"

    function_full_names = {k: get_fullname(v) for k, v in function_registry.items()}
    return json.dumps(function_full_names, indent=2, ensure_ascii=False)


@typechecked
async def invoke_function(name: str, arguments: dict):
    if name not in function_registry:
        raise ValueError(f"Function '{name}' not found in the constructors.")
    func = function_registry[name]

    args = arguments
    if not isinstance(args, dict):
        raise ValueError("Arguments must be a JSON object.")
    # print(f"FunctionRegistry: Invoking function '{name}' with arguments: {args}")

    result = await func(**args)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Function Registry CLI')
    subparsers = parser.add_subparsers(dest='command')
    # Subparser for the 'list' command
    list_parser = subparsers.add_parser('list', help='List all functions as JSON')
    # Subparser for the 'invoke' command
    invoke_parser = subparsers.add_parser('invoke', help='Invoke a function by name with arguments')
    invoke_parser.add_argument('--name', required=True, help='Name of the function to invoke')
    invoke_parser.add_argument('--arguments', required=True, help='JSON string of arguments to pass to the function')
    # Parse the arguments
    args = parser.parse_args()
    if args.command == 'list':
        print(asyncio.run(list_functions()))
    elif args.command == 'invoke':
        asyncio.run(invoke_function(args.name, args.arguments))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
