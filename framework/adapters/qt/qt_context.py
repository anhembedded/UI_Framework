from PySide6.QtCore import QObject, Signal

from framework.core.task_context import TaskContext
from framework.core.task_state import TaskStatus


class QtTaskSignals(QObject):
    """Qt signals emitted by a running task.

    Must live on a QObject so Qt's signal-slot queued connections work
    across threads (worker thread → GUI thread).
    """

    progress = Signal(int)           # 0–100
    message = Signal(str)            # human-readable status string
    error = Signal(str)              # error description
    finished = Signal(object)        # TaskStatus value


class QtTaskContext(TaskContext):
    """TaskContext implementation that emits Qt signals.

    The Worker (QRunnable) calls methods here; Qt automatically queues
    the signals to the GUI thread via a queued connection.
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = QtTaskSignals()
        self._cancelled: bool = False

    # ------------------------------------------------------------------
    # TaskContext interface
    # ------------------------------------------------------------------

    def report_progress(self, value: int) -> None:
        self.signals.progress.emit(value)

    def report_message(self, message: str) -> None:
        self.signals.message.emit(message)

    def log(self, message: str) -> None:
        # Route log output through the message signal so the UI can show it.
        self.signals.message.emit(f"[LOG] {message}")

    def is_cancelled(self) -> bool:
        return self._cancelled

    # ------------------------------------------------------------------
    # Qt-specific extension
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Set the cancellation flag.  Called from the GUI thread via TaskHandle."""
        self._cancelled = True
