from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QLabel,
)
from PySide6.QtCore import Qt

from framework.core.task_state import TaskStatus
from framework.ui.views.base_qt_view import BaseQtView


class ITaskSubView(BaseQtView):
    start_btn: QPushButton
    cancel_btn: QPushButton
    def set_running(self) -> None: ...
    def set_message(self, text: str) -> None: ...
    def set_progress(self, value: int) -> None: ...
    def set_finished(self, status: TaskStatus) -> None: ...


class TaskSubView(ITaskSubView):
    """Content widget for an MDI sub-window.

    Inherits BaseQtView so that when the parent QMdiSubWindow
    is destroyed, `closeEvent` fires and triggers `presenter.cleanup()`.
    """

    def __init__(self, task_name: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.task_name = task_name
        self._build_ui()
        self.set_idle()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.name_label = QLabel(f"<b>{self.task_name}</b>")
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)

        self.status_label = QLabel("Ready — press Start.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start")
        self.cancel_btn = QPushButton("✕ Cancel")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # State helpers called by presenter
    # ------------------------------------------------------------------

    def set_idle(self) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(0)

    def set_running(self) -> None:
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText("Running…")

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def set_message(self, text: str) -> None:
        self.status_label.setText(text)

    def set_finished(self, status: TaskStatus) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        msgs = {
            TaskStatus.COMPLETED: "✅ Done",
            TaskStatus.CANCELLED: "⚠️ Cancelled",
            TaskStatus.FAILED:    "❌ Failed",
        }
        self.status_label.setText(msgs.get(status, str(status)))
