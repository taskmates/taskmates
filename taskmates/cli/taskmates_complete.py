import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

from loguru import logger
from typeguard import typechecked

from taskmates.cli.complete import complete
from taskmates.config import CompletionContext, ServerConfig, CompletionOpts, ClientConfig, CLIENT_CONFIG, \
    SERVER_CONFIG, COMPLETION_CONTEXT, COMPLETION_OPTS

debug = os.environ.get("TASKMATES_DEBUG", "false") in ["1", "true"]

if not debug:
    logging.getLogger().setLevel(logging.ERROR)

    logger.remove()
    logger.add(sys.stderr, level="ERROR")
    # file_logger.remove()


def merge_template_params(template_params: list) -> dict:
    merged_params = {}
    for param_dict in template_params:
        merged_params.update(param_dict)
    return merged_params


def main():
    parser = argparse.ArgumentParser(description='Taskmates CLI Tool')
    parser.add_argument('markdown', type=str, help='The markdown content', nargs='?')
    parser.add_argument('--format', type=str, choices=['full', 'original', 'text', 'completion'], default='text',
                        help='The output format')
    parser.add_argument('--output', type=str, help='The output file path')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='The websocket endpoint')
    parser.add_argument('--model', type=str, default='claude-3-opus-20240229', help='The model to use')
    parser.add_argument('-n', '--max-interactions', type=int, default=float('inf'),
                        help='The maximum number of interactions')
    parser.add_argument('--template-params', type=json.loads, action='append', default=[],
                        help='JSON string with system prompt template parameters (can be specified multiple times)')
    args = parser.parse_args()

    markdown = get_markdown(args)

    request_id = str(uuid4())

    # If --output is not provided, write to request_id file in /var/tmp
    output = args.output or f"/var/tmp/taskmates/completions/{request_id}.md"
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    context: CompletionContext = {
        "request_id": request_id,
        "markdown_path": str(Path(os.getcwd()) / f"{request_id}.md"),
        "cwd": os.getcwd(),
    }
    COMPLETION_CONTEXT.set({**COMPLETION_CONTEXT.get(), **context})

    client_config = ClientConfig(interactive=False,
                                 format=args.format,
                                 endpoint=args.endpoint,
                                 output=(output if args.output else None))
    CLIENT_CONFIG.set({**CLIENT_CONFIG.get(), **client_config})

    server_config: ServerConfig = {
        "taskmates_dir": os.environ.get("TASKMATES_HOME", "/var/tmp/taskmates"),
    }
    SERVER_CONFIG.set({**SERVER_CONFIG.get(), **server_config})

    completion_opts: CompletionOpts = {
        "model": args.model,
        "template_params": merge_template_params(args.template_params),
        'max_interactions': args.max_interactions,
    }

    COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})

    asyncio.run(complete(markdown, context, client_config))

    # # Print the output to stdout
    # with open(output, 'r') as f:
    #     print(f.read())


@typechecked
def get_markdown(args) -> str:
    # Read markdown from stdin if available
    stdin_markdown = ""
    # if not os.isatty(sys.stdin.fileno()):
    pycharm_env = os.environ.get("PYCHARM_HOSTED", 0) == '1'
    if not pycharm_env and not sys.stdin.isatty():
        stdin_markdown = "".join(sys.stdin.readlines())
        # data = sys.stdin.readlines()
        # stdin_markdown = "\n".join(data)
    # Concatenate stdin markdown with --markdown argument if both are provided
    args_markdown = args.markdown

    if stdin_markdown and args_markdown:
        markdown = stdin_markdown + "\n**user** " + args_markdown
    elif stdin_markdown:
        markdown = stdin_markdown
    elif args_markdown:
        markdown = args_markdown
    else:
        raise ValueError("No markdown provided")
    return markdown


if __name__ == '__main__':
    main()


def test_merge_template_params():
    template_params = [
        {"key1": "value1"},
        {"key2": "value2"},
        {"key1": "overridden_value"}
    ]
    merged_params = merge_template_params(template_params)
    assert merged_params == {"key1": "overridden_value", "key2": "value2"}
