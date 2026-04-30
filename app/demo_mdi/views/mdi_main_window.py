"""MDI Main Window — QMainWindow with QMdiArea + live log console.

The log console captures Python logging output from any thread via a
thread-safe Qt signal bridge, so cleanup messages from worker threads
appear instantly in the UI.
"""

import logging

from PySide6.QtWidgets import (
    QMainWindow, QMdiArea, QMdiSubWindow, QDockWidget,
    QTextEdit, QWidget, QToolBar, QStatusBar,
)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QAction, QColor


# ---------------------------------------------------------------------------
# Thread-safe logging bridge
# ---------------------------------------------------------------------------

class _LogEmitter(QObject):
    """Emits a string signal — usable from any thread."""
    record = Signal(str, int)   # (formatted_text, levelno)


class QtLogHandler(logging.Handler):
    """Logging handler that routes records to a Qt signal (thread-safe)."""

    COLORS = {
        logging.DEBUG:    "#888888",
        logging.INFO:     "#cccccc",
        logging.WARNING:  "#f0a500",
        logging.ERROR:    "#e05555",
        logging.CRITICAL: "#ff3333",
    }

    def __init__(self) -> None:
        super().__init__()
        self.emitter = _LogEmitter()
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s]  %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.record.emit(self.format(record), record.levelno)
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MdiMainWindow(QMainWindow):
    """QMainWindow with QMdiArea and a live cleanup log dock.

    NOT a BaseQtView (it's a QMainWindow), but BasePresenter still hooks
    into `view.destroyed` as the cleanup trigger.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Demo — MDI Lifecycle Test  (open & close windows)")
        self.resize(960, 680)
        self._build_ui()
        self._install_log_handler()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Central MDI area
        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setBackground(Qt.darkGray)
        self.setCentralWidget(self.mdi_area)

        # Toolbar
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.action_new      = QAction("➕  New Task Window", self)
        self.action_cascade  = QAction("⊞  Cascade", self)
        self.action_tile     = QAction("⊟  Tile", self)
        self.action_close_all = QAction("✕  Close All", self)

        tb.addAction(self.action_new)
        tb.addSeparator()
        tb.addAction(self.action_cascade)
        tb.addAction(self.action_tile)
        tb.addSeparator()
        tb.addAction(self.action_close_all)

        self.action_cascade.triggered.connect(self.mdi_area.cascadeSubWindows)
        self.action_tile.triggered.connect(self.mdi_area.tileSubWindows)
        self.action_close_all.triggered.connect(self.mdi_area.closeAllSubWindows)
        self.mdi_area.subWindowActivated.connect(self._on_sub_activated)

        # Log dock (bottom)
        dock = QDockWidget("🔍  Lifecycle Log", self)
        dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self._log_console = QTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setMinimumHeight(130)
        self._log_console.setMaximumHeight(200)
        self._log_console.setStyleSheet(
            "background:#1e1e1e; color:#cccccc; font-family:Consolas,monospace; font-size:11px;"
        )
        self._log_console.setPlaceholderText(
            "Open sub-windows, start tasks, then CLOSE them — cleanup events appear here."
        )
        dock.setWidget(self._log_console)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready — use ➕ to open task windows.")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _install_log_handler(self) -> None:
        self._log_handler = QtLogHandler()
        self._log_handler.emitter.record.connect(self._append_log)
        logging.getLogger().addHandler(self._log_handler)

    def _append_log(self, text: str, levelno: int) -> None:
        color = QtLogHandler.COLORS.get(levelno, "#cccccc")
        self._log_console.append(f'<span style="color:{color}">{text}</span>')
        sb = self._log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ------------------------------------------------------------------
    # MDI helpers (called by presenter)
    # ------------------------------------------------------------------

    def add_sub_window(self, widget: QWidget, title: str) -> QMdiSubWindow:
        """Wrap *widget* in a QMdiSubWindow and show it.

        WA_DeleteOnClose ensures that when the sub-window X is clicked,
        the QMdiSubWindow is destroyed, which destroys its child widget,
        which fires `widget.destroyed` → BasePresenter._on_view_destroyed()
        → cleanup().
        """
        sub = QMdiSubWindow()
        sub.setAttribute(Qt.WA_DeleteOnClose)
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.resize(360, 230)
        self.mdi_area.addSubWindow(sub)
        sub.show()
        return sub

    def update_status(self, text: str) -> None:
        self._status_bar.showMessage(text)

    def _on_sub_activated(self, sub) -> None:
        count = len(self.mdi_area.subWindowList())
        self._status_bar.showMessage(
            f"{count} sub-window(s) open." if count else "No sub-windows open."
        )

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Close all sub-windows first so each triggers its own cleanup."""
        self.mdi_area.closeAllSubWindows()
        logging.getLogger().removeHandler(self._log_handler)
        super().closeEvent(event)
