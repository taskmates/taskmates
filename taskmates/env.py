import os

from taskmates import patches


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


def bootstrap():
    # check whether already bootstrapped
    if hasattr(bootstrap, "_initialized"):
        return

    bootstrap._initialized = True

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
