import taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execute_markdown_on_local_kernel
import taskmates.core.markdown_chat.parse_markdown_chat
import taskmates.core.markdown_chat.parse_front_matter_and_messages
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution import \
    execute_markdown_on_local_kernel
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflow_engine.run import Run
from taskmates.lib.opentelemetry_.wrap_function import wrap_function
from taskmates.lib.opentelemetry_.wrap_module import wrap_module
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


def instrument():
    SubclassExtensionPoints.subscribe(Run, wrap_module)
    SubclassExtensionPoints.subscribe(CompletionProvider, wrap_module)
    wrap_function(taskmates.core.markdown_chat.parse_markdown_chat, 'parse_markdown_chat')
    wrap_function(taskmates.core.markdown_chat.parse_front_matter_and_messages, 'parse_front_matter_and_messages')
    wrap_function(execute_markdown_on_local_kernel, 'execute_markdown_on_local_kernel')
