#!/usr/bin/env python3

import argparse
import sys

import tiktoken

tokenizer = tiktoken.encoding_for_model("gpt-4")


def count_tokens(text: str) -> int:
    """count the number of tokens in a string"""
    return len(tokenizer.encode(text))


def main(input=sys.stdin, args_list=sys.argv[1:]) -> int:
    parser = argparse.ArgumentParser(
        description="Count the number of tokens in a string",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "file", nargs="?", help="File name to read the text from", type=argparse.FileType('r'), default=input
    )
    args = parser.parse_args(args_list)

    # Reads from the file directly or from stdin if no file is provided
    text = args.file.read()
    print(count_tokens(text))


if __name__ == "__main__":
    main()


def test_count_tokens():
    assert count_tokens("Hello, world!") == 4
    assert count_tokens("") == 0
