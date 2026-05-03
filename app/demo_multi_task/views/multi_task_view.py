from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QLabel, QGroupBox, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt
from framework.core.task_state import TaskStatus
from framework.ui.views.base_qt_view import BaseQtView


class ITaskCard(QGroupBox):
    cancel_btn: QPushButton
    def set_progress(self, value: int) -> None: ...
    def set_message(self, text: str) -> None: ...
    def set_finished(self, status: TaskStatus) -> None: ...


class TaskCard(ITaskCard):
    """A small widget representing one running task."""

    def __init__(self, task_id: str, name: str, parent=None) -> None:
        super().__init__(name, parent)
        self.task_id = task_id
        layout = QHBoxLayout(self)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(200)

        self.status_label = QLabel("Running…")
        self.status_label.setMinimumWidth(160)

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedWidth(32)

        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.cancel_btn)

    def set_progress(self, value: int) -> None:
        self.progress.setValue(value)

    def set_message(self, text: str) -> None:
        self.status_label.setText(text)

    def set_finished(self, status: TaskStatus) -> None:
        self.cancel_btn.setEnabled(False)
        icons = {
            TaskStatus.COMPLETED: "✅ Done",
            TaskStatus.CANCELLED: "⚠️ Cancelled",
            TaskStatus.FAILED:    "❌ Failed",
        }
        self.status_label.setText(icons.get(status, str(status)))


class IMultiTaskView(BaseQtView):
    add_btn: QPushButton
    cancel_all_btn: QPushButton
    clear_btn: QPushButton
    def add_card(self, task_id: str, name: str) -> ITaskCard: ...
    def remove_finished_cards(self) -> None: ...
    def set_summary(self, text: str) -> None: ...


class MultiTaskView(IMultiTaskView):
    """View that allows spawning multiple parallel tasks."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Demo — Parallel Multi-Task Runner")
        self.setMinimumSize(560, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        self.add_btn = QPushButton("➕  Add Task")
        self.clear_btn = QPushButton("🗑  Clear Finished")
        self.cancel_all_btn = QPushButton("✕  Cancel All")
        top.addWidget(self.add_btn)
        top.addWidget(self.clear_btn)
        top.addStretch()
        top.addWidget(self.cancel_all_btn)
        root.addLayout(top)

        # Scroll area for task cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setAlignment(Qt.AlignTop)
        self._card_layout.setSpacing(6)
        scroll.setWidget(self._card_container)
        root.addWidget(scroll)

        # Summary
        self.summary_label = QLabel("No tasks yet.")
        self.summary_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.summary_label)

    # ------------------------------------------------------------------
    # Called by presenter
    # ------------------------------------------------------------------

    def add_card(self, task_id: str, name: str) -> TaskCard:
        card = TaskCard(task_id, name)
        self._card_layout.addWidget(card)
        return card

    def remove_finished_cards(self) -> None:
        for i in reversed(range(self._card_layout.count())):
            item = self._card_layout.itemAt(i)
            if item and isinstance(item.widget(), TaskCard):
                card: TaskCard = item.widget()
                if not card.cancel_btn.isEnabled():
                    card.setParent(None)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)
