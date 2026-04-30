from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Type


class TaskFactory(ABC):
    """Abstract factory that creates a specific Task instance."""

    @abstractmethod
    def create(self):
        """Instantiate and return a Task."""
        pass


class TaskRegistry:
    """Maps task type keys to their factories, enabling lookup-based creation.

    Usage:
        registry = TaskRegistry()
        registry.register("download", DownloadTaskFactory)
        task = registry.create("download", url="...", save_path="...")
    """

    def __init__(self) -> None:
        self._map: Dict[Any, Callable] = {}

    def register(self, task_type: Any, factory: Callable) -> None:
        """Associate a task_type key with a callable factory."""
        self._map[task_type] = factory

    def create(self, task_type: Any, *args: Any, **kwargs: Any):
        """Instantiate a task by its registered type key."""
        factory = self._map.get(task_type)
        if factory is None:
            raise KeyError(f"No factory registered for task type: {task_type!r}")
        return factory(*args, **kwargs)
