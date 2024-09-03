# TODO
# import contextlib
# from typing import Iterator
#
# from taskmates.runner.contexts.contexts import Contexts
# from taskmates.sdk.experimental.taskmates_extension import TaskmatesExtension
#
#
# class TestExtension(TaskmatesExtension):
#     @property
#     def name(self) -> str:
#         return "TestExtension"
#
#     @contextlib.contextmanager
#     def completion_context(self, history: str | None,
#                            incoming_messages: list[str],
#                            contexts: Contexts) -> Iterator[tuple[str | None, list[str], Contexts]]:
#         yield "modified_history", ["modified_messages"], {"modified_contexts": True}
#
#
# class CaptureContext(TaskmatesExtension):
#     def __init__(self):
#         self.captured_args = {}
#
#     @property
#     def name(self) -> str:
#         return "CaptureContext"
#
#     @contextlib.contextmanager
#     def completion_context(self, *args):
#         self.captured_args['completion_context'] = args
#         yield args
#
#     @contextlib.contextmanager
#     def completion_step_context(self, *args):
#         self.captured_args['completion_step_context'] = args
#         yield args
