"""BaseQtView — QWidget subclass with managed presenter lifecycle.

Every application view MUST inherit from this class (not QWidget directly).
It ensures that when the user closes a window, the presenter's cleanup()
is automatically called, which cancels all running tasks.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QCloseEvent


class BaseQtView(QWidget):
    """Base class for all Qt application views.

    Lifecycle contract:
        1. After creation, call ``view._set_presenter(presenter)``.
        2. When the user closes the window, ``closeEvent`` fires.
        3. ``closeEvent`` calls ``presenter.cleanup()``.
        4. ``cleanup()`` cancels all active tasks and drops the view reference.

    Subclasses should override UI-only methods (``set_progress``, etc.).
    They must NOT contain business logic.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._presenter = None

    def _set_presenter(self, presenter) -> None:
        """Wire the presenter so closeEvent can reach it."""
        self._presenter = presenter

    def closeEvent(self, event: QCloseEvent) -> None:
        """Trigger presenter cleanup before the window closes."""
        if self._presenter is not None:
            self._presenter.cleanup()
            self._presenter = None
        super().closeEvent(event)
