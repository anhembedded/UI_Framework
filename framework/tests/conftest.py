"""Shared pytest fixtures and task stubs for framework tests.

Design decisions:
    - Task stubs are real Task subclasses (not mocks) so tests remain
      resistant to refactoring — they exercise actual framework contracts.
    - MagicMock is used ONLY at the true system boundary (executor mock
      in framework integration tests).
    - No Qt imports here — all tests in tests/framework/ are fast/pure Python.
"""

import pytest
from unittest.mock import MagicMock

from framework.core.task import AbstractTask
from framework.core.task_state import TaskState, TaskStatus


# ---------------------------------------------------------------------------
# Task stubs
# ---------------------------------------------------------------------------

class SuccessTask(AbstractTask):
    """Completes immediately with return value 'ok'."""
    def run(self, ctx):
        ctx.report_progress(100)
        ctx.report_message("done")
        ctx.log("SuccessTask finished")
        return "ok"


class CancelCheckTask(AbstractTask):
    """Checks cancellation each step. Returns None if cancelled."""
    def __init__(self, steps: int = 5) -> None:
        self.steps = steps

    def run(self, ctx):
        for i in range(self.steps):
            if ctx.is_cancelled():
                return None
            ctx.report_progress(int((i + 1) / self.steps * 100))
        return "finished"


class FailTask(AbstractTask):
    """Raises ValueError immediately."""
    def run(self, ctx):
        raise ValueError("intentional_error")


class SlowTask(AbstractTask):
    """Sleeps per step — only used in timeout integration tests."""
    def __init__(self, sleep_sec: float = 2.0) -> None:
        self.sleep_sec = sleep_sec

    def run(self, ctx):
        import time
        time.sleep(self.sleep_sec)
        return "slow_result"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def success_task() -> AbstractTask:
    return SuccessTask()


@pytest.fixture
def cancel_task() -> AbstractTask:
    return CancelCheckTask(steps=5)


@pytest.fixture
def fail_task() -> AbstractTask:
    return FailTask()


@pytest.fixture
def sample_state() -> TaskState:
    return TaskState(id="test-id", status=TaskStatus.PENDING)
