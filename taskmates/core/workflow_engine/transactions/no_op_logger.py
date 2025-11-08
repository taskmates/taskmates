class NoOpLogger:
    """No-op logger when there's no active transaction."""

    def info(self, message: str) -> None:
        pass

    def debug(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


_noop_logger = NoOpLogger()
