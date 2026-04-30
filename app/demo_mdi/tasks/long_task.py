import time
from framework.core.task import Task


class LongTask(Task):
    """A deliberately long-running task designed to test the cleanup mechanism.

    Runs for `duration` seconds (1 step / second).
    Logs cancellation explicitly so the MDI log console can show it.
    """

    def __init__(self, name: str, duration: int = 20) -> None:
        self.name = name
        self.duration = duration

    def run(self, ctx):
        for i in range(self.duration):
            if ctx.is_cancelled():
                ctx.log(f"[{self.name}] ⚠️ Cancelled at step {i + 1}/{self.duration}")
                ctx.report_message(f"[{self.name}] Cancelled.")
                return None

            time.sleep(1)
            pct = int((i + 1) / self.duration * 100)
            ctx.report_progress(pct)
            ctx.report_message(f"[{self.name}] step {i + 1}/{self.duration}")

        ctx.log(f"[{self.name}] ✅ All {self.duration} steps complete.")
        return f"{self.name}: done"
