"""BasePresenter — foundation for all application presenters.

Thread-safety and lifecycle rules:
    1. Call ``super().bind(view)`` as the FIRST line of every subclass ``bind()``.
    2. Call ``view._set_presenter(self)`` as the SECOND line.
    3. Every task handle returned by executor.submit() MUST be _track()-ed.
    4. Every callback that touches ``self.view`` MUST guard with:
           if not self.is_alive: return
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional


class BasePresenter:
    """Base class for all application presenters.

    Attributes:
        executor: The TaskExecutor used to submit domain tasks.
        view:     The bound view widget (None after cleanup).
        _handles: List of active TaskHandle objects for lifecycle management.
    """

    def __init__(self, executor) -> None:
        self.executor = executor
        self.view: Optional[Any] = None
        self._handles: List[Any] = []
        self._logger = logging.getLogger(type(self).__name__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def bind(self, view) -> None:
        """Bind this presenter to a view.

        Connects to ``view.destroyed`` signal if available (Qt safety net).
        Subclasses MUST call ``super().bind(view)`` first.
        """
        self.view = view
        try:
            view.destroyed.connect(self._on_view_destroyed)
        except AttributeError:
            pass   # non-Qt views (e.g. QMainWindow wired manually) — OK

    def cleanup(self) -> None:
        """Cancel all tracked tasks and drop the view reference.

        Safe to call multiple times (idempotent).
        """
        for handle in list(self._handles):
            try:
                handle.cancel()
            except Exception:
                pass
        self._handles.clear()
        self.view = None
        self._logger.debug("Presenter cleaned up: %s", type(self).__name__)

    def _on_view_destroyed(self) -> None:
        """Secondary cleanup trigger — fires when Qt destroys the widget."""
        if self.view is not None:
            self.cleanup()

    # ------------------------------------------------------------------
    # Handle tracking helpers
    # ------------------------------------------------------------------

    def _track(self, handle) -> None:
        """Register a TaskHandle for lifecycle management."""
        self._handles.append(handle)

    def _untrack(self, handle) -> None:
        """Remove a TaskHandle when it completes (before checking is_alive)."""
        try:
            self._handles.remove(handle)
        except ValueError:
            pass  # already removed — idempotent

    # ------------------------------------------------------------------
    # Guard property (P0 — non-negotiable)
    # ------------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        """Return True if the view is still alive and can receive updates.

        ALL presenter callbacks that touch ``self.view`` MUST start with::

            if not self.is_alive: return
        """
        return self.view is not None
