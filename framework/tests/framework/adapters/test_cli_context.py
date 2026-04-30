"""Tests for CLITaskContext — stdout adapter behaviour.

4-criterion focus:
  Regression    : all 5 abstract methods including cancel()
  Refactor-safe : tests visible behaviour (capsys output, flag state),
                  not print() call count
  Fast feedback : synchronous, no I/O wait
  Maintainability: uses pytest capsys, grouped by method
"""

import pytest
import logging
from framework.adapters.cli.cli_context import CLITaskContext


@pytest.fixture
def ctx() -> CLITaskContext:
    return CLITaskContext()


class TestCLITaskContextProgress:
    def test_report_progress_prints_percentage(self, ctx, capsys):
        # Arrange / Act
        ctx.report_progress(42)
        # Assert
        assert "42" in capsys.readouterr().out

    def test_report_progress_100_is_printed(self, ctx, capsys):
        ctx.report_progress(100)
        assert "100" in capsys.readouterr().out


class TestCLITaskContextMessage:
    def test_report_message_prints_text(self, ctx, capsys):
        ctx.report_message("hello from task")
        assert "hello from task" in capsys.readouterr().out


class TestCLITaskContextLog:
    def test_log_does_not_print_to_stdout(self, ctx, capsys):
        """log() must go to Python logging, NOT stdout — regression guard."""
        ctx.log("debug line")
        out = capsys.readouterr().out
        assert "debug line" not in out   # not in stdout

    def test_log_emits_to_python_logger(self, ctx, caplog):
        with caplog.at_level(logging.DEBUG):
            ctx.log("logged message")
        assert "logged message" in caplog.text


class TestCLITaskContextCancellation:
    def test_is_cancelled_returns_false_initially(self, ctx):
        assert ctx.is_cancelled() is False

    def test_cancel_makes_is_cancelled_return_true(self, ctx):
        # Arrange
        assert not ctx.is_cancelled()
        # Act
        ctx.cancel()
        # Assert
        assert ctx.is_cancelled() is True

    def test_cancel_is_idempotent(self, ctx):
        ctx.cancel()
        ctx.cancel()   # second call must not raise
        assert ctx.is_cancelled()
