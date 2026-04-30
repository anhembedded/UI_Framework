"""Tests for TaskContext ABC enforcement.

4-criterion focus:
  Regression    : ensures ABC contract is never silently broken
  Refactor-safe : tests the public contract (TypeError on missing methods),
                  not internal ABC machinery
  Fast feedback : instantaneous — pure Python ABC checks
  Maintainability: minimal, impossible to misread
"""

import pytest
from framework.core.task_context import TaskContext


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------

class TestTaskContextABC:
    def test_cannot_instantiate_task_context_directly(self):
        # Arrange / Act / Assert
        with pytest.raises(TypeError):
            TaskContext()

    def test_subclass_missing_report_progress_raises_type_error(self):
        class Incomplete(TaskContext):
            def report_message(self, m): pass
            def log(self, m): pass
            def is_cancelled(self): return False
            def cancel(self): pass
        with pytest.raises(TypeError):
            Incomplete()

    def test_subclass_missing_cancel_raises_type_error(self):
        """cancel() was added in v2 — regression test to prevent silent removal."""
        class MissingCancel(TaskContext):
            def report_progress(self, v): pass
            def report_message(self, m): pass
            def log(self, m): pass
            def is_cancelled(self): return False
        with pytest.raises(TypeError):
            MissingCancel()

    def test_complete_subclass_instantiates_successfully(self):
        class ConcreteCtx(TaskContext):
            def report_progress(self, v): pass
            def report_message(self, m): pass
            def log(self, m): pass
            def is_cancelled(self): return False
            def cancel(self): pass

        # Should not raise
        ctx = ConcreteCtx()
        assert ctx is not None
