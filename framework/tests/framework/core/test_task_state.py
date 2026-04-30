"""Tests for TaskState — thread-safety, locked setters, snapshot immutability.

4-criterion focus:
  Regression       : covers all public mutators + snapshot
  Refactor-safe    : tests behaviour (state values), not internal _lock mechanics
  Fast feedback    : no I/O, no sleep; concurrent test uses short-lived threads
  Maintainability  : one behaviour per test, descriptive names
"""

import threading
import pytest
from framework.core.task_state import TaskState, TaskStatus


# ---------------------------------------------------------------------------
# Arrange helper
# ---------------------------------------------------------------------------

def make_state(status: TaskStatus = TaskStatus.PENDING) -> TaskState:
    return TaskState(id="abc", status=status)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestTaskStateDefaults:
    def test_default_progress_is_zero(self):
        # Arrange / Act
        state = make_state()
        # Assert
        assert state.progress == 0

    def test_default_result_is_none(self):
        state = make_state()
        assert state.result is None

    def test_default_error_is_none(self):
        state = make_state()
        assert state.error is None


# ---------------------------------------------------------------------------
# Locked setters
# ---------------------------------------------------------------------------

class TestTaskStateSetters:
    def test_set_status_updates_status(self):
        # Arrange
        state = make_state(TaskStatus.PENDING)
        # Act
        state.set_status(TaskStatus.RUNNING)
        # Assert
        assert state.status == TaskStatus.RUNNING

    def test_set_result_updates_result(self):
        state = make_state()
        state.set_result({"key": "value"})
        assert state.result == {"key": "value"}

    def test_set_error_updates_error(self):
        state = make_state()
        state.set_error("something went wrong")
        assert state.error == "something went wrong"

    def test_set_progress_updates_progress(self):
        state = make_state()
        state.set_progress(75)
        assert state.progress == 75

    def test_set_status_accepts_all_enum_values(self):
        state = make_state()
        for status in TaskStatus:
            state.set_status(status)
            assert state.status == status


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestTaskStateSnapshot:
    def test_snapshot_returns_copy_not_reference(self):
        # Arrange
        state = make_state(TaskStatus.RUNNING)
        # Act
        snap = state.snapshot()
        state.set_status(TaskStatus.COMPLETED)   # mutate original
        # Assert — snapshot is unaffected
        assert snap.status == TaskStatus.RUNNING

    def test_snapshot_values_match_at_capture_time(self):
        state = make_state()
        state.set_progress(42)
        state.set_result("done")
        snap = state.snapshot()
        assert snap.progress == 42
        assert snap.result == "done"

    def test_snapshot_id_matches_original(self):
        state = TaskState(id="unique-id", status=TaskStatus.PENDING)
        snap = state.snapshot()
        assert snap.id == "unique-id"


# ---------------------------------------------------------------------------
# Thread safety (regression protection for concurrent mutation bug)
# ---------------------------------------------------------------------------

class TestTaskStateThreadSafety:
    def test_concurrent_status_mutations_do_not_corrupt_state(self):
        """
        Multiple threads hammering set_status() must not cause
        data corruption or exceptions.  We cannot assert a specific
        final value (scheduling is non-deterministic), but the object
        must always hold a valid TaskStatus member.
        """
        # Arrange
        state = make_state()
        statuses = list(TaskStatus)
        errors = []

        def worker(s: TaskStatus):
            try:
                for _ in range(50):
                    state.set_status(s)
            except Exception as exc:
                errors.append(exc)

        # Act
        threads = [threading.Thread(target=worker, args=(s,)) for s in statuses]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert errors == [], f"Thread errors: {errors}"
        assert state.status in TaskStatus   # still a valid enum member
