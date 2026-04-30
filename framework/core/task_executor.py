from abc import ABC, abstractmethod
from typing import Any, Callable


class TaskHandle:
    """Unified interface for controlling and observing a submitted task.

    Works identically for both Qt and CLI runtimes.
    """

    def cancel(self) -> None:
        """Request the task to stop as soon as possible."""
        pass

    def subscribe(self, callback: Callable[[Any], None]) -> None:
        """Register a callback to receive progress or state updates."""
        pass

    def get_state(self):
        """Return the current TaskState snapshot."""
        pass


class TaskExecutor(ABC):
    """Entry point for submitting tasks to a runtime backend."""

    @abstractmethod
    def submit(self, task) -> TaskHandle:
        """Submit a Task for execution and return a handle to control it."""
        pass
