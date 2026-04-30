import logging

from ui.presenters.base_presenter import BasePresenter
from app.demo_mdi.views.task_sub_view import TaskSubView
from app.demo_mdi.presenters.task_sub_presenter import TaskSubPresenter

_logger = logging.getLogger(__name__)
_counter = 0


class MdiMainPresenter(BasePresenter):
    """Manages the MDI main window.

    Responsibilities:
    - Opens new sub-windows on demand (each with its own TaskSubPresenter)
    - Tracks the count of open windows in the status bar
    - Does NOT hold strong references to sub-presenters — each sub-presenter
      is owned by its view via _set_presenter; cleanup is automatic.
    """

    def bind(self, view) -> None:
        super().bind(view)
        # MdiMainWindow is a QMainWindow, not a BaseQtView, but
        # BasePresenter.bind() still connects to view.destroyed as safety net.
        view.action_new.triggered.connect(self.on_new_window)
        _logger.info(
            "═══════════════════════════════════════════\n"
            "  MDI Lifecycle Test started.\n"
            "  Open sub-windows → start tasks → close windows.\n"
            "  Watch this log for CLEANUP events.\n"
            "═══════════════════════════════════════════"
        )

    def on_new_window(self) -> None:
        global _counter
        _counter += 1
        name = f"Task-{_counter}"

        sub_view = TaskSubView(task_name=name)
        sub_presenter = TaskSubPresenter(self.executor, task_name=name)
        sub_presenter.bind(sub_view)

        if self.is_alive:
            self.view.add_sub_window(sub_view, f"Worker: {name}")
            self._refresh_status()
            _logger.info("📂 OPEN — Sub-window '%s' created.", name)

    def _refresh_status(self) -> None:
        if not self.is_alive:
            return
        count = len(self.view.mdi_area.subWindowList())
        self.view.update_status(
            f"{count} sub-window(s) open.  Close one to see cleanup in the log."
            if count else "No sub-windows open."
        )
