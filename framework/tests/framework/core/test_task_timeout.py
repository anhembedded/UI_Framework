"""Tests for WithTimeout — auto-cancellation on expiry.

4-criterion focus:
  Regression    : task-completes-before-timeout + task-exceeds-timeout paths
  Refactor-safe : tests OBSERVABLE behaviour (ctx.is_cancelled(), elapsed time),
                  not Timer internals
  Fast feedback : timeouts are < 0.2 s to keep suite fast
  Maintainability: two clear scenarios, self-explanatory names
"""

import time
import pytest
from framework.core.task_timeout import WithTimeout
from framework.core.task import AbstractTask
from framework.adapters.cli.cli_context import CLITaskContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FastTask(AbstractTask):
    """Completes in ~0 ms — should NOT be cancelled by timeout."""
    def run(self, ctx):
        return "fast_result"


class _SlowTask(AbstractTask):
    """Sleeps 5 s — will be cancelled by a short timeout."""
    def run(self, ctx):
        for _ in range(50):
            if ctx.is_cancelled():
                return None
            time.sleep(0.1)
        return "slow_result"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWithTimeout:
    def test_fast_task_returns_result_when_within_timeout(self):
        # Arrange
        ctx = CLITaskContext()
        task = WithTimeout(_FastTask(), timeout_sec=5.0)
        # Act
        result = task.run(ctx)
        # Assert
        assert result == "fast_result"
        assert not ctx.is_cancelled()

    def test_slow_task_receives_cancellation_when_timeout_expires(self):
        # Arrange
        ctx = CLITaskContext()
        task = WithTimeout(_SlowTask(), timeout_sec=0.15)
        # Act
        start = time.monotonic()
        result = task.run(ctx)
        elapsed = time.monotonic() - start
        # Assert — cancelled early, not 5 s
        assert ctx.is_cancelled()
        assert result is None
        assert elapsed < 2.0, f"Should have stopped early, took {elapsed:.2f}s"

    def test_timeout_does_not_cancel_ctx_before_expiry(self):
        """Timer must NOT fire before the task completes."""
        # Arrange
        ctx = CLITaskContext()
        task = WithTimeout(_FastTask(), timeout_sec=2.0)
        # Act
        task.run(ctx)
        # Assert — context should be clean
        assert not ctx.is_cancelled()
