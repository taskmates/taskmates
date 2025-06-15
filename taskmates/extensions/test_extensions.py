# TODO
# import contextlib
# from typing import Iterator
#
# from taskmates.runner.context.context import Context
# from taskmates.sdk.experimental.taskmates_extension import TaskmatesExtension
#
#
# class TestExtension(TaskmatesExtension):
#     @property
#     def name(self) -> str:
#         return "TestExtension"
#
#     @contextlib.contextmanager
#     def runner_environment(self, history: str | None,
#                            incoming_messages: list[str],
#                            context: Context) -> Iterator[tuple[str | None, list[str], Context]]:
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
#     def runner_environment(self, *args):
#         self.captured_args['runner_environment'] = args
#         yield args
#
#     @contextlib.contextmanager
#     def completion_step_context(self, *args):
#         self.captured_args['completion_step_context'] = args
#         yield args
