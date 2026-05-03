"""Tests for CLITaskExecutor — synchronous execution contract.

4-criterion focus:
  Regression    : COMPLETED / FAILED / CANCELLED states; subscribe() warning;
                  repo integration
  Refactor-safe : asserts on TaskState values and warning category,
                  not on internal implementation details
  Fast feedback : synchronous executor, no threads, no sleep
  Maintainability: fixture provides executor; tests are independent
"""

import warnings
import pytest
from framework.runtime.cli_executor import CLITaskExecutor
from framework.core.task_repository import TaskRepository
from framework.core.task_state import TaskStatus
from framework.tests.conftest import SuccessTask, FailTask, CancelCheckTask


@pytest.fixture
def executor() -> CLITaskExecutor:
    return CLITaskExecutor()


@pytest.fixture
def executor_with_repo():
    repo = TaskRepository()
    return CLITaskExecutor(repo=repo), repo


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------

class TestCLITaskExecutorSuccess:
    def test_submit_success_task_returns_completed_status(self, executor):
        # Arrange / Act
        handle = executor.submit(SuccessTask())
        state = handle.get_state()
        # Assert
        assert state.status == TaskStatus.COMPLETED

    def test_submit_success_task_stores_result(self, executor):
        handle = executor.submit(SuccessTask())
        assert handle.get_state().result == "ok"

    def test_submit_success_task_has_no_error(self, executor):
        handle = executor.submit(SuccessTask())
        assert handle.get_state().error is None


# ---------------------------------------------------------------------------
# Failure execution
# ---------------------------------------------------------------------------

class TestCLITaskExecutorFailure:
    def test_submit_failing_task_returns_failed_status(self, executor):
        handle = executor.submit(FailTask())
        assert handle.get_state().status == TaskStatus.FAILED

    def test_submit_failing_task_stores_error_message(self, executor):
        handle = executor.submit(FailTask())
        assert "intentional_error" in handle.get_state().error

    def test_submit_failing_task_does_not_propagate_exception(self, executor):
        """Executor must catch exceptions — regression guard against bare raise."""
        # Act — should not raise
        handle = executor.submit(FailTask())
        assert handle is not None


# ---------------------------------------------------------------------------
# Cancellation — CLI is synchronous, pre-cancel is only real test
# ---------------------------------------------------------------------------

class TestCLITaskExecutorCancellation:
    def test_pre_cancelled_context_causes_cancelled_status(self):
        """
        CLITaskContext can be cancelled externally (e.g. WithTimeout).
        Pre-setting cancel before submit is the observable equivalent.
        We achieve this via a task that always reports cancelled.
        """
        from framework.core.task import AbstractTask
        class AlwaysCancelTask(AbstractTask):
            def run(self, ctx):
                ctx.cancel()          # cancels itself
                if ctx.is_cancelled():
                    return None
                return "should_not_reach"

        handle = CLITaskExecutor().submit(AlwaysCancelTask())
        assert handle.get_state().status == TaskStatus.CANCELLED


# ---------------------------------------------------------------------------
# Repository integration
# ---------------------------------------------------------------------------

class TestCLITaskExecutorRepository:
    def test_submit_stores_state_in_repo(self, executor_with_repo):
        executor, repo = executor_with_repo
        handle = executor.submit(SuccessTask())
        task_id = handle.get_state().id
        assert repo.get(task_id) is not None

    def test_submit_updates_repo_to_completed(self, executor_with_repo):
        executor, repo = executor_with_repo
        handle = executor.submit(SuccessTask())
        task_id = handle.get_state().id
        assert repo.get(task_id).status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# P0 regression: subscribe() must warn, not silently fail
# ---------------------------------------------------------------------------

class TestCLITaskHandleSubscribe:
    def test_subscribe_raises_user_warning(self, executor):
        handle = executor.submit(SuccessTask())
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            handle.subscribe(lambda: None)
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "CLITaskHandle" in str(caught[0].message)

    def test_get_state_returns_snapshot_not_live_reference(self, executor):
        handle = executor.submit(SuccessTask())
        snap1 = handle.get_state()
        snap2 = handle.get_state()
        # Two snapshots should be equal in value but independent objects
        assert snap1 is not snap2
        assert snap1.status == snap2.status
