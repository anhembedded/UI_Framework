import logging

from framework.core.task_context import TaskContext

_logger = logging.getLogger(__name__)


class CLITaskContext(TaskContext):
    """TaskContext implementation that writes to stdout and Python logging.

    Used by CLITaskExecutor for command-line/headless execution.
    """

    def __init__(self) -> None:
        self._cancelled: bool = False

    # ------------------------------------------------------------------
    # TaskContext interface
    # ------------------------------------------------------------------

    def report_progress(self, value: int) -> None:
        print(f"[PROGRESS] {value}%")

    def report_message(self, message: str) -> None:
        print(f"[INFO] {message}")

    def log(self, message: str) -> None:
        """Route to Python logging — NOT stdout (P1 fix)."""
        _logger.debug(message)


    def is_cancelled(self) -> bool:
        return self._cancelled

    # ------------------------------------------------------------------
    # CLI-specific extension
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request cancellation (useful when running in a background thread)."""
        self._cancelled = True
