import taskmates.actions.parse_markdown_chat
import taskmates.formats.markdown.parsing.parse_front_matter_and_messages
import taskmates.core.actions.code_execution.code_cells.execute_markdown_on_local_kernel
from taskmates.core.completion_provider import CompletionProvider
from taskmates.lib.opentelemetry_.wrap_function import wrap_function
from taskmates.lib.opentelemetry_.wrap_module import wrap_module
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints
from taskmates.workflow_engine.run import Run


def instrument():
    SubclassExtensionPoints.subscribe(Run, wrap_module)
    SubclassExtensionPoints.subscribe(CompletionProvider, wrap_module)
    wrap_function(taskmates.actions.parse_markdown_chat, 'parse_markdown_chat')
    wrap_function(taskmates.formats.markdown.parsing.parse_front_matter_and_messages, 'parse_front_matter_and_messages')
    wrap_function(taskmates.core.actions.code_execution.code_cells.execute_markdown_on_local_kernel, 'execute_markdown_on_local_kernel')


