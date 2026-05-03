from __future__ import annotations
import json
import copy
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskState:
    """Snapshot of a task's current execution state.

    Thread-safety:
        Mutations (from worker thread) and reads (from GUI thread) are
        protected by an internal lock.  Call ``snapshot()`` from the GUI
        thread to get a consistent, lock-free copy.
    """

    id: str
    status: TaskStatus
    progress: int = 0
    result: Any = None
    error: Optional[str] = None

    # Lock is excluded from dataclass comparisons / repr
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )

    def snapshot(self) -> TaskState:
        """Return a thread-safe shallow copy (safe to read from any thread)."""
        with self._lock:
            return copy.copy(self)

    def set_status(self, status: TaskStatus) -> None:
        with self._lock:
            self.status = status

    def set_result(self, result: Any) -> None:
        with self._lock:
            self.result = result

    def set_error(self, error: str) -> None:
        with self._lock:
            self.error = error

    def set_progress(self, value: int) -> None:
        with self._lock:
            self.progress = value
    def __str__(self) -> str:   
        with self._lock:
            data = {
                "id": self.id,
                "status": str(self.status),
            "progress": self.progress,
            "result": str(self.result),
            "error": self.error
        }
        return f"TaskState:{json.dumps(data)}"

