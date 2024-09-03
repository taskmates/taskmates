from taskmates.core.actions.code_execution.shell.run_shell_command import run_shell_command
from taskmates.defaults.tools.chroma_.chromadb_search import chromadb_search
from taskmates.defaults.tools.dalle_.convert_to_svg import convert_to_svg
from taskmates.defaults.tools.dalle_.generate_images import generate_images
from taskmates.defaults.tools.evaluation_.report_evaluation import report_evaluation
from taskmates.defaults.tools.filesystem_.read_file import read_file
from taskmates.defaults.tools.filesystem_.write_file import write_file
from taskmates.defaults.tools.google_ import google_search
from taskmates.defaults.tools.jira_.jira_ import create_issue, add_comment, update_status, search_issues, delete_issues, \
    dump_context, \
    read_issue
from taskmates.defaults.tools.test_.echo import echo

tools_registry = {}


def initialize_function_registry(function_registry):
    # debugging
    function_registry["echo"] = echo

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


initialize_function_registry(tools_registry)
