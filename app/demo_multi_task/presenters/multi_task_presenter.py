from typing import Dict, Any
from framework.ui.presenters.base_presenter import BasePresenter
from app.demo_multi_task.tasks.work_task import WorkTask
from framework.core.task_state import TaskStatus
from app.demo_multi_task.views.multi_task_view import IMultiTaskView


class MultiTaskPresenter(BasePresenter):
    """Presenter for MultiTaskView.

    Demonstrates multi-handle tracking: multiple tasks run in parallel,
    each with its own card widget and progress bar.
    """

    view: IMultiTaskView
    _task_counter: int = 0

    def bind(self, view: IMultiTaskView) -> None:
        super().bind(view)
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)
        self._card_map: Dict = {}  # handle → TaskCard

        view.add_btn.clicked.connect(self.on_add_task)
        view.cancel_all_btn.clicked.connect(self.on_cancel_all)
        view.clear_btn.clicked.connect(self.on_clear_finished)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def on_add_task(self) -> None:
        MultiTaskPresenter._task_counter += 1
        name = f"Worker-{self._task_counter}"
        task = WorkTask(name=name, steps=6, step_delay=0.6)
        handle = self.executor.submit(task)
        self._track(handle)

        if self.is_alive:
            card = self.view.add_card(id(handle), name)
            self._card_map[id(handle)] = card
            card.cancel_btn.clicked.connect(lambda checked=False, h=handle: h.cancel())

        handle.subscribe(lambda v, h=handle: self._on_progress(h, v))
        handle.subscribe_message(lambda m, h=handle: self._on_message(h, m))
        handle.subscribe_finished(lambda s, h=handle: self._on_finished(h, s))
        self._update_summary()

    def on_cancel_all(self) -> None:
        for h in list(self._handles):
            h.cancel()

    def on_clear_finished(self) -> None:
        if self.is_alive:
            self.view.remove_finished_cards()

    # ------------------------------------------------------------------
    # Per-task callbacks — P0 is_alive guard on each
    # ------------------------------------------------------------------

    def _on_progress(self, handle, value: int) -> None:
        if not self.is_alive:
            return
        card = self._card_map.get(id(handle))
        if card:
            card.set_progress(value)

    def _on_message(self, handle, message: str) -> None:
        if not self.is_alive:
            return
        card = self._card_map.get(id(handle))
        if card:
            card.set_message(message)

    def _on_finished(self, handle, status: TaskStatus) -> None:
        self._untrack(handle)
        if not self.is_alive:
            return
        card = self._card_map.pop(id(handle), None)
        if card:
            card.set_finished(status)
        self._update_summary()

    def _update_summary(self) -> None:
        if not self.is_alive:
            return
        active = len(self._handles)
        self.view.set_summary(
            f"{active} task(s) running." if active else "All tasks complete."
        )
