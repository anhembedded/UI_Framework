"""
framework.bootstrap — Composition Root / DI Container
=====================================================
Version : 1.0.0
SDD     : Design/SDD/SDD_bootstrap.md

This module provides FrameworkContext, the lightweight DI Container
that acts as the Single Point of Wiring.

It creates and owns ALL shared services in one place:
  - TaskRepository
  - TaskExecutor (Qt or CLI)
  - PresenterFactory

The App layer (AppFactory) NEVER creates these services manually.
It only calls FrameworkContext.qt() or FrameworkContext.cli() once,
then uses the fluent API to register and wire.
"""

from typing import Any, Tuple, Type
from framework.core.task_repository import TaskRepository
from framework.ui.presenters.presenter_factory import PresenterFactory
from framework.core.task_executor import TaskExecutor


class FrameworkContext:
    """Lightweight DI container — Single Point of Wiring.

    Rules:
        1. Create ONCE per application lifecycle.
        2. Never instantiate TaskExecutor or TaskRepository outside this class.
        3. Use ``ctx.wire(view)`` to create and bind presenters.
    """

    def __init__(self, executor: TaskExecutor, repo: TaskRepository):
        self.executor = executor
        self.repo = repo
        self.presenter_factory = PresenterFactory()

    @staticmethod
    def qt() -> 'FrameworkContext':
        """Bootstrap the Qt GUI runtime."""
        from framework.runtime.qt_executor import QtTaskExecutor
        repo = TaskRepository()
        executor = QtTaskExecutor(repo=repo)
        return FrameworkContext(executor, repo)

    @staticmethod
    def cli() -> 'FrameworkContext':
        """Bootstrap the CLI / headless runtime."""
        from framework.runtime.cli_executor import CLITaskExecutor
        repo = TaskRepository()
        executor = CLITaskExecutor(repo=repo)
        return FrameworkContext(executor, repo)

    def register(self, view_cls: Type, presenter_cls: Type) -> 'FrameworkContext':
        """Register a view-presenter pair."""
        self.presenter_factory.register(view_cls, presenter_cls)
        return self

    def wire(self, view: Any) -> Tuple[Any, Any]:
        """Create and fully bind the registered presenter for *view*."""
        presenter = self.presenter_factory.create(view, self.executor)
        presenter.bind(view)
        return view, presenter
