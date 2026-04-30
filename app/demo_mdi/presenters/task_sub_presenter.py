import logging

from ui.presenters.base_presenter import BasePresenter
from app.demo_mdi.tasks.long_task import LongTask
from framework.core.task_state import TaskStatus

_logger = logging.getLogger(__name__)


class TaskSubPresenter(BasePresenter):
    """Presenter for a single MDI sub-window (TaskSubView).

    Overrides cleanup() to add explicit logging so the MDI log console
    can show evidence of the cleanup lifecycle.
    """

    def __init__(self, executor, task_name: str) -> None:
        super().__init__(executor)
        self.task_name = task_name

    def bind(self, view) -> None:
        super().bind(view)
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)
        view.start_btn.clicked.connect(self.on_start)
        view.cancel_btn.clicked.connect(self.on_cancel)

    # ------------------------------------------------------------------
    # Lifecycle override — adds visibility into cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        active = len(self._handles)
        _logger.info(
            "🧹 CLEANUP — Presenter '%s' | active tasks: %d | "
            "cancelling now…",
            self.task_name, active,
        )
        super().cleanup()
        _logger.info(
            "✅ CLEANUP DONE — Presenter '%s' | view=None handles=[]",
            self.task_name,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def on_start(self) -> None:
        task = LongTask(name=self.task_name, duration=20)
        handle = self.executor.submit(task)
        self._track(handle)

        handle.subscribe(self.on_progress)
        handle.subscribe_message(self.on_message)
        handle.subscribe_finished(lambda s, h=handle: self.on_finished(s, h))
        handle.subscribe_error(self.on_error)

        if self.is_alive:
            self.view.set_running()

        _logger.info("▶ START — Task '%s' submitted to executor.", self.task_name)

    def on_cancel(self) -> None:
        for h in list(self._handles):
            h.cancel()
        if self.is_alive:
            self.view.set_message("Cancelling…")

    # ------------------------------------------------------------------
    # Task callbacks — ALL guarded with is_alive (P0)
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
        _logger.info(
            "⏹ FINISHED — Task '%s' → %s", self.task_name, status.name
        )
        if not self.is_alive:
            _logger.debug(
                "  (view already gone — is_alive=False, skipping UI update)"
            )
            return
        self.view.set_finished(status)

    def on_error(self, error_msg: str) -> None:
        _logger.error("❌ ERROR — Task '%s': %s", self.task_name, error_msg)
        if not self.is_alive:
            return
        self.view.set_message(f"❌ {error_msg}")
