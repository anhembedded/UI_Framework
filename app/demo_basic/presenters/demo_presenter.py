from ui.presenters.base_presenter import BasePresenter
from app.demo_basic.tasks.demo_task import DemoTask
from framework.core.task_state import TaskStatus


class DemoPresenter(BasePresenter):
    """Presenter for DemoView — basic progress demo."""

    def bind(self, view) -> None:
        super().bind(view)
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)
        view.start_button.clicked.connect(self.on_start)
        view.cancel_button.clicked.connect(self.on_cancel)

    # ------------------------------------------------------------------
    # User actions
    # ------------------------------------------------------------------

    def on_start(self) -> None:
        handle = self.executor.submit(DemoTask())
        self._track(handle)
        handle.subscribe(self.on_progress)
        handle.subscribe_message(self.on_message)
        handle.subscribe_finished(lambda s, h=handle: self.on_finished(s, h))
        handle.subscribe_error(self.on_error)
        if self.is_alive:
            self.view.set_running()

    def on_cancel(self) -> None:
        for h in list(self._handles):
            h.cancel()
        if self.is_alive:
            self.view.set_message("Cancellation requested…")

    # ------------------------------------------------------------------
    # Task callbacks — P0: is_alive guard on every callback
    # ------------------------------------------------------------------

    def on_progress(self, value: int) -> None:
        if not self.is_alive:
            return
        self.view.set_progress(value)

    def on_message(self, message: str) -> None:
        if not self.is_alive:
            return
        self.view.set_message(message)

    def on_finished(self, status: TaskStatus, handle=None) -> None:
        if handle:
            self._untrack(handle)
        if not self.is_alive:
            return
        self.view.set_finished(status)

    def on_error(self, error_msg: str) -> None:
        if not self.is_alive:
            return
        self.view.set_message(f"Error: {error_msg}")
