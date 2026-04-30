import uuid
from typing import Callable, List, Optional

from PySide6.QtCore import QRunnable, QThreadPool

from framework.core.task_executor import TaskExecutor, TaskHandle
from framework.core.task_state import TaskState, TaskStatus
from framework.adapters.qt.qt_context import QtTaskContext


class QtTaskHandle(TaskHandle):
    """Controls and observes a Qt-backed task submission."""

    def __init__(self, state: TaskState, ctx: QtTaskContext) -> None:
        self._state = state
        self.ctx = ctx

    def cancel(self) -> None:
        self.ctx.cancel()

    def subscribe(self, callback: Callable) -> None:
        """Connect *callback* to the progress signal (GUI-thread safe)."""
        self.ctx.signals.progress.connect(callback)

    def subscribe_message(self, callback: Callable) -> None:
        self.ctx.signals.message.connect(callback)

    def subscribe_finished(self, callback: Callable) -> None:
        self.ctx.signals.finished.connect(callback)

    def subscribe_error(self, callback: Callable) -> None:
        self.ctx.signals.error.connect(callback)

    def get_state(self) -> TaskState:
        """Return a thread-safe snapshot of the current state."""
        return self._state.snapshot()


class QtTaskRunner(QRunnable):
    """QRunnable that wraps a Task and runs it in QThreadPool's worker thread."""

    def __init__(
        self,
        task,
        ctx: QtTaskContext,
        state: TaskState,
        repo=None,
    ) -> None:
        super().__init__()
        self.task = task
        self.ctx = ctx
        self.state = state
        self._repo = repo

    def run(self) -> None:
        try:
            self.state.set_status(TaskStatus.RUNNING)
            if self._repo:
                self._repo.update(self.state)

            result = self.task.run(self.ctx)

            if self.ctx.is_cancelled():
                self.state.set_status(TaskStatus.CANCELLED)
                self.ctx.signals.finished.emit(TaskStatus.CANCELLED)
            else:
                self.state.set_result(result)
                self.state.set_status(TaskStatus.COMPLETED)
                self.ctx.signals.finished.emit(TaskStatus.COMPLETED)

        except Exception as exc:
            self.state.set_error(str(exc))
            self.state.set_status(TaskStatus.FAILED)
            self.ctx.signals.error.emit(str(exc))
            self.ctx.signals.finished.emit(TaskStatus.FAILED)

        finally:
            if self._repo:
                self._repo.update(self.state)


class QtTaskExecutor(TaskExecutor):
    """TaskExecutor backed by Qt's QThreadPool."""

    def __init__(self, repo=None) -> None:
        self.pool = QThreadPool.globalInstance()
        self._repo = repo

    def submit(self, task) -> QtTaskHandle:
        ctx = QtTaskContext()
        state = TaskState(id=str(uuid.uuid4()), status=TaskStatus.PENDING)

        if self._repo:
            self._repo.add(state)

        runner = QtTaskRunner(task, ctx, state, repo=self._repo)
        handle = QtTaskHandle(state, ctx)

        self.pool.start(runner)
        return handle
