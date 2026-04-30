import logging
import warnings
import uuid

from framework.core.task_executor import TaskExecutor, TaskHandle
from framework.core.task_state import TaskState, TaskStatus
from framework.adapters.cli.cli_context import CLITaskContext

_logger = logging.getLogger(__name__)


class CLITaskHandle(TaskHandle):
    """TaskHandle for synchronous CLI execution."""

    def __init__(self, state: TaskState) -> None:
        self._state = state

    def cancel(self) -> None:
        # Synchronous execution is already finished when handle is returned.
        pass

    def subscribe(self, callback) -> None:
        # P0 FIX: Warn loudly instead of silently doing nothing.
        warnings.warn(
            "CLITaskHandle.subscribe() has no effect. "
            "CLI execution is synchronous — use get_state() after submit() instead.",
            stacklevel=2,
        )
        _logger.warning("CLITaskHandle.subscribe() called but has no effect (synchronous mode).")

    def get_state(self) -> TaskState:
        return self._state.snapshot()


class CLITaskExecutor(TaskExecutor):
    """TaskExecutor that runs tasks synchronously in the calling thread."""

    def __init__(self, repo=None) -> None:
        self._repo = repo

    def submit(self, task) -> CLITaskHandle:
        ctx = CLITaskContext()
        state = TaskState(id=str(uuid.uuid4()), status=TaskStatus.RUNNING)

        if self._repo:
            self._repo.add(state)

        try:
            result = task.run(ctx)
            if ctx.is_cancelled():
                state.set_status(TaskStatus.CANCELLED)
            else:
                state.set_result(result)
                state.set_status(TaskStatus.COMPLETED)

        except Exception as exc:
            _logger.exception("Task %s raised an unhandled exception.", state.id)
            state.set_error(str(exc))
            state.set_status(TaskStatus.FAILED)

        finally:
            if self._repo:
                self._repo.update(state)

        return CLITaskHandle(state)
