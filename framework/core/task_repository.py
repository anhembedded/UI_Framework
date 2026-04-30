from typing import Dict, Optional
from framework.core.task_state import TaskState


class TaskRepository:
    """In-memory store that acts as the single source of truth for TaskState.

    Executors write state updates here; presenters can query state if needed.
    Future versions may emit events when state changes.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskState] = {}

    def add(self, state: TaskState) -> None:
        """Register a new task state."""
        self._tasks[state.id] = state

    def update(self, state: TaskState) -> None:
        """Overwrite an existing task state entry."""
        self._tasks[state.id] = state

    def get(self, task_id: str) -> Optional[TaskState]:
        """Retrieve a task state by its unique ID."""
        return self._tasks.get(task_id)

    def all(self) -> Dict[str, TaskState]:
        """Return all stored task states."""
        return dict(self._tasks)
