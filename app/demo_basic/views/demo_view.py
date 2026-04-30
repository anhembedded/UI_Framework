from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QLabel, QWidget,
)
from PySide6.QtCore import Qt
from framework.core.task_state import TaskStatus
from ui.views.base_qt_view import BaseQtView


class DemoView(BaseQtView):
    """Basic demo view: Start, Cancel, progress bar, message label."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Demo — Basic Progress Task")
        self.setMinimumWidth(420)
        self._build_ui()
        self.set_idle()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.message_label = QLabel("Press Start to run the demo task.")
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.start_button = QPushButton("▶  Start")
        self.cancel_button = QPushButton("✕  Cancel")
        btn_row.addWidget(self.start_button)
        btn_row.addWidget(self.cancel_button)
        layout.addLayout(btn_row)

    def set_idle(self) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def set_running(self) -> None:
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.set_message("Task is running…")

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def set_message(self, text: str) -> None:
        self.message_label.setText(text)

    def set_finished(self, status: TaskStatus) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        messages = {
            TaskStatus.COMPLETED: "✅  Task completed.",
            TaskStatus.CANCELLED: "⚠️  Task cancelled.",
            TaskStatus.FAILED:    "❌  Task failed.",
        }
        self.set_message(messages.get(status, str(status)))
        if status == TaskStatus.COMPLETED:
            self.progress_bar.setValue(100)
