import time
from framework.core.task_context import TaskContext
from framework.core.task import AbstractTask


class WorkTask(AbstractTask):
    """Simulated multi-step work task. Used to demo parallel execution."""

    def __init__(self, name: str, steps: int = 6, step_delay: float = 0.7) -> None:
        self.name = name
        self.steps = steps
        self.step_delay = step_delay

    def run(self, ctx: TaskContext):
        for i in range(self.steps):
            if ctx.is_cancelled():
                ctx.report_message(f"[{self.name}] Cancelled at step {i}.")
                return None
            time.sleep(self.step_delay)
            pct = int((i + 1) / self.steps * 100)
            ctx.report_progress(pct)
            ctx.report_message(f"[{self.name}] step {i + 1}/{self.steps}")
        return f"{self.name}: complete"
