"""Task timeout wrapper — P2 improvement.

Wraps any Task to enforce a maximum execution time.
If the task exceeds the timeout, cancellation is requested automatically.

Usage::

    task = WithTimeout(MyHeavyTask(), timeout_sec=30.0)
    handle = executor.submit(task)
"""

import threading
from framework.core.task import Task


class WithTimeout(Task):
    """Decorator-style Task wrapper that enforces a maximum run time.

    When the timeout expires, ``ctx.cancel()`` is called automatically.
    The wrapped task is responsible for checking ``ctx.is_cancelled()``
    regularly and returning early.
    """

    def __init__(self, task: Task, timeout_sec: float) -> None:
        self._task = task
        self._timeout = timeout_sec

    def run(self, ctx):
        timer = threading.Timer(self._timeout, ctx.cancel)
        try:
            timer.start()
            return self._task.run(ctx)
        finally:
            timer.cancel()
