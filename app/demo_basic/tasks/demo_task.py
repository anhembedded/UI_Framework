import time
from framework.core.task import AbstractTask


class DemoTask(AbstractTask):
    """Basic demo task: counts 5 steps, reports progress each second."""

    def run(self, ctx):
        for i in range(5):
            if ctx.is_cancelled():
                ctx.report_message("Task cancelled.")
                return None
            time.sleep(1)
            progress = (i + 1) * 20
            ctx.report_progress(progress)
            ctx.report_message(f"Step {i + 1}/5 complete ({progress}%)")
        return "Done"
