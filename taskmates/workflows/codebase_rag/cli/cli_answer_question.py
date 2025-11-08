#!/usr/bin/env python3
"""
CLI tool to answer questions about a codebase using RAG.
"""
import argparse
import asyncio
import json

from taskmates.core.workflow_engine.transaction_manager import TransactionManager, runtime
from taskmates.workflows.codebase_rag.sdk.answer_question import answer_question


async def async_main(args):
    transaction_manager = TransactionManager(cache_dir=args.cache_dir)
    
    with runtime.transaction_manager_context(transaction_manager):
        answer_result = await answer_question(
            question=args.question,
            project_root=args.project_root,
            file_pattern=args.file_pattern
        )

    if args.output_format == "json":
        print(json.dumps(answer_result, indent=2))
    else:
        print(f"=== Answer ===\n{answer_result['answer']}\n")
        print(f"=== Citations ===")
        for citation in answer_result['citations']:
            print(f"  - {citation}")
        print(f"\n=== Code Snippets ({len(answer_result['code_snippets'])}) ===")
        for snippet in answer_result['code_snippets']:
            print(f"\n--- {snippet['uri']} ---")
            print(snippet['content'])


def main():
    parser = argparse.ArgumentParser(
        description="Answer questions about a codebase using RAG"
    )
    parser.add_argument("question", help="The question to answer")
    parser.add_argument("--project-root", required=True, help="Root directory of the project")
    parser.add_argument("--file-pattern", default="*.py", help="File pattern to match (default: *.py)")
    parser.add_argument("--cache-dir", required=True, help="Cache directory for transaction manager")
    parser.add_argument("--output-format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
