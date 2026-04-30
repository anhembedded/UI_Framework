from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QFileDialog, QHeaderView,
)
from PySide6.QtCore import Qt
from framework.core.task_state import TaskStatus
from ui.views.base_qt_view import BaseQtView


class FileProcessorView(BaseQtView):
    """View for the file-scan demo: directory picker, results table."""

    COLUMNS = ["File", "Rel. Path", "Lines", "Words", "Size (KB)"]

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Demo — File Processor  (30 s timeout)")
        self.setMinimumSize(700, 500)
        self._build_ui()
        self.set_idle()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Directory row
        dir_row = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select a directory…")
        self.browse_btn = QPushButton("📂 Browse")
        dir_row.addWidget(self.dir_input)
        dir_row.addWidget(self.browse_btn)
        root.addLayout(dir_row)

        # Controls
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Scan")
        self.cancel_btn = QPushButton("✕  Cancel")
        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.cancel_btn)
        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("Choose a directory and press Scan.")
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)

        # Results table
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def get_directory(self) -> str:
        return self.dir_input.text().strip()

    def set_idle(self) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(0)

    def set_running(self) -> None:
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.table.setRowCount(0)
        self.set_status("Scanning…")

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_finished(self, status: TaskStatus) -> None:
        self.set_idle()
        msgs = {
            TaskStatus.COMPLETED: "✅  Scan complete.",
            TaskStatus.CANCELLED: "⚠️  Scan cancelled (timeout or user).",
            TaskStatus.FAILED:    "❌  Scan failed.",
        }
        self.set_status(msgs.get(status, str(status)))

    def populate_results(self, results: list) -> None:
        self.table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(r.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("rel_path", "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(r.get("lines", 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(r.get("words", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(r.get("size_kb", 0))))
