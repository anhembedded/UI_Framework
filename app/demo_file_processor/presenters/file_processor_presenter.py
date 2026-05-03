from PySide6.QtWidgets import QFileDialog

from framework.ui.presenters.base_presenter import BasePresenter
from app.demo_file_processor.tasks.file_scan_task import FileScanTask
from framework.core.task_state import TaskStatus
from framework.core.task_timeout import WithTimeout
from app.demo_file_processor.views.file_processor_view import IFileProcessorView

SCAN_TIMEOUT_SEC = 30.0


class FileProcessorPresenter(BasePresenter):
    """Presenter for FileProcessorView.

    Demonstrates:
    - P2 WithTimeout: scan is capped at 30 seconds
    - P0 is_alive guard on every callback
    - P1 multi-handle tracking
    """
    
    view: IFileProcessorView

    def bind(self, view: IFileProcessorView) -> None:
        super().bind(view)
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)
        view.browse_btn.clicked.connect(self.on_browse)
        view.start_btn.clicked.connect(self.on_start)
        view.cancel_btn.clicked.connect(self.on_cancel)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def on_browse(self) -> None:
        if not self.is_alive:
            return
        directory = QFileDialog.getExistingDirectory(
            self.view, "Select Directory", ""
        )
        if directory:
            self.view.dir_input.setText(directory)

    def on_start(self) -> None:
        if not self.is_alive:
            return
        directory = self.view.get_directory()
        if not directory:
            self.view.set_status("⚠️  Please select a directory first.")
            return

        task = WithTimeout(FileScanTask(directory), timeout_sec=SCAN_TIMEOUT_SEC)
        handle = self.executor.submit(task)
        self._track(handle)

        handle.subscribe(self.on_progress)
        handle.subscribe_message(self.on_message)
        handle.subscribe_finished(lambda s, h=handle: self.on_finished(s, h))
        handle.subscribe_error(self.on_error)

        self.view.set_running()

    def on_cancel(self) -> None:
        for h in list(self._handles):
            h.cancel()
        if self.is_alive:
            self.view.set_status("Cancellation requested…")

    # ------------------------------------------------------------------
    # Task callbacks — P0 is_alive guard on every one
    # ------------------------------------------------------------------

    def on_progress(self, value: int) -> None:
        if not self.is_alive:
            return
        self.view.set_progress(value)

    def on_message(self, message: str) -> None:
        if not self.is_alive:
            return
        self.view.set_status(message)

    def on_finished(self, status: TaskStatus, handle=None) -> None:
        if handle:
            self._untrack(handle)
            # Read results from the handle before it's released
            state = handle.get_state()
            if state.result and isinstance(state.result, dict):
                results = state.result.get("results", [])
                if self.is_alive:
                    self.view.populate_results(results)

        if not self.is_alive:
            return
        self.view.set_finished(status)

    def on_error(self, error_msg: str) -> None:
        if not self.is_alive:
            return
        self.view.set_status(f"❌ Error: {error_msg}")
