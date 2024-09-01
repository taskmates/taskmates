import contextvars
import os

from taskmates import patches
from taskmates.sdk.experimental.extension_manager import EXTENSION_MANAGER
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


# Register the custom finder
# if os.environ.get('TASKMATES_TELEMETRY_ENABLED', '0') == '1':
#     if not any(isinstance(finder, CustomFinder) for finder in sys.meta_path):
#         sys.meta_path.insert(0, CustomFinder())

# class ColorHandler(logging.StreamHandler):
#     # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
#     GRAY8 = "38;5;8"
#     GRAY7 = "38;5;7"
#     ORANGE = "33"
#     RED = "31"
#     WHITE = "0"
#
#     def emit(self, record):
#         # We don't use white for any logging, to help distinguish from user print statements
#         level_color_map = {
#             logging.DEBUG: self.GRAY8,
#             logging.INFO: self.GRAY7,
#             logging.WARNING: self.ORANGE,
#             logging.ERROR: self.RED,
#         }
#
#         csi = f"{chr(27)}["  # control sequence introducer
#         color = level_color_map.get(record.levelno, self.WHITE)
#
#         self.stream.write(f"{csi}{color}m{record.msg}{csi}m\n")

class TaskmatesRuntime:
    @staticmethod
    def bootstrap():
        # check whether already bootstrapped
        if hasattr(TaskmatesRuntime, "_initialized") and TaskmatesRuntime._initialized:
            return

        TaskmatesRuntime._initialized = True

        # # # See https://no-color.org/
        # if not os.environ.get("NO_COLOR"):
        #     logging.root.addHandler(ColorHandler())

        # if not logging.root.hasHandlers():
        #     handler = logging.StreamHandler()
        #     handler.setLevel(logging.INFO)
        #     logging.root.addHandler(handler)
        #
        # logging.root.setLevel(logging.INFO)

        patches.install()

        if os.environ.get('TASKMATES_TELEMETRY_ENABLED', '0') == '1':
            from taskmates.instrumentation import taskmates_instrumentor
            taskmates_instrumentor.instrument()

        SubclassExtensionPoints.initialize()
        EXTENSION_MANAGER.get().initialize()

    @staticmethod
    def shutdown():
        SubclassExtensionPoints.cleanup()
        EXTENSION_MANAGER.get().shutdown()
        TaskmatesRuntime._initialized = False


taskmates_runtime = TaskmatesRuntime()

TASKMATES_RUNTIME: contextvars.ContextVar[TaskmatesRuntime] = contextvars.ContextVar("taskmates_runtime",
                                                                                     default=taskmates_runtime)
