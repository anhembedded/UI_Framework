from abc import ABC, abstractmethod
from typing import Any


class AbstractTask(ABC):
    """Base class for all domain tasks.
    
    Tasks are pure domain logic — no dependency on Qt or any UI framework.
    """

    @abstractmethod
    def run(self, ctx) -> Any:
        """Execute the task logic.
        
        Args:
            ctx: A TaskContext instance used to report progress, messages,
                 and check for cancellation.

        Returns:
            Any result value, or None.
        """
        pass
