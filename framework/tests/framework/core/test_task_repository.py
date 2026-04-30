"""Tests for TaskRepository — CRUD and isolation.

4-criterion focus:
  Regression    : all CRUD paths including edge cases (unknown id, overwrite)
  Refactor-safe : tests public API only, not internal dict structure
  Fast feedback : pure in-memory, no I/O
  Maintainability: each test is self-contained, uses fixture for state
"""

import pytest
from framework.core.task_repository import TaskRepository
from framework.core.task_state import TaskState, TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(id: str = "t1", status: TaskStatus = TaskStatus.PENDING) -> TaskState:
    return TaskState(id=id, status=status)


@pytest.fixture
def repo() -> TaskRepository:
    return TaskRepository()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTaskRepositoryAdd:
    def test_add_makes_state_retrievable(self, repo):
        # Arrange
        state = make_state("t1")
        # Act
        repo.add(state)
        # Assert
        assert repo.get("t1") is not None

    def test_add_preserves_id(self, repo):
        state = make_state("unique-42")
        repo.add(state)
        assert repo.get("unique-42").id == "unique-42"

    def test_add_preserves_status(self, repo):
        state = make_state("t1", TaskStatus.RUNNING)
        repo.add(state)
        assert repo.get("t1").status == TaskStatus.RUNNING


class TestTaskRepositoryGet:
    def test_get_unknown_id_returns_none(self, repo):
        # Arrange (empty repo)
        # Act / Assert
        assert repo.get("nonexistent") is None

    def test_get_returns_same_object_reference(self, repo):
        state = make_state("t1")
        repo.add(state)
        assert repo.get("t1") is state


class TestTaskRepositoryUpdate:
    def test_update_overwrites_existing_entry(self, repo):
        # Arrange
        original = make_state("t1", TaskStatus.PENDING)
        repo.add(original)
        updated = make_state("t1", TaskStatus.COMPLETED)
        # Act
        repo.update(updated)
        # Assert
        assert repo.get("t1").status == TaskStatus.COMPLETED

    def test_update_with_new_id_creates_entry(self, repo):
        """update() behaves like upsert — regression guard."""
        state = make_state("new-id", TaskStatus.RUNNING)
        repo.update(state)
        assert repo.get("new-id") is not None


class TestTaskRepositoryAll:
    def test_all_returns_all_added_states(self, repo):
        # Arrange
        for i in range(3):
            repo.add(make_state(f"t{i}"))
        # Act
        result = repo.all()
        # Assert
        assert len(result) == 3

    def test_all_returns_copy_not_internal_reference(self, repo):
        """Mutating the returned dict must not affect the repository."""
        repo.add(make_state("t1"))
        result = repo.all()
        result.clear()          # mutate copy
        assert repo.get("t1") is not None  # original unaffected

    def test_all_empty_repo_returns_empty_dict(self, repo):
        assert repo.all() == {}
