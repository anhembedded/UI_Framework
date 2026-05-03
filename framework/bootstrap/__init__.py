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

from __future__ import annotations

from typing import Any, Tuple, Type, TYPE_CHECKING

from framework.core.task_repository import TaskRepository
from framework.ui.presenters.presenter_factory import PresenterFactory

if TYPE_CHECKING:
    from framework.core.task_executor import TaskExecutor


class FrameworkContext:
    """Lightweight DI container — Single Point of Wiring.

    Rules:
        1. Create ONCE per application lifecycle (inside BaseApp.run()).
        2. Never instantiate TaskExecutor or TaskRepository outside this class.
        3. Use ``ctx.wire(view)`` to create and bind presenters — never call
           PresenterFactory.create() and presenter.bind() separately.

    Attributes:
        executor:          The active TaskExecutor for this runtime.
        repo:              The TaskRepository (single source of truth for state).
        presenter_factory: The PresenterFactory registry.
    """

    def __init__(self, executor: "TaskExecutor", repo: TaskRepository) -> None:
        self.executor = executor
        self.repo = repo
        self.presenter_factory = PresenterFactory()

    # ------------------------------------------------------------------
    # Runtime factory methods — one per supported runtime
    # ------------------------------------------------------------------

    @classmethod
    def qt(cls) -> "FrameworkContext":
        """Bootstrap the Qt GUI runtime.

        Creates a TaskRepository and QtTaskExecutor (backed by QThreadPool).
        Call this inside a QtApp.run() after QApplication is created.
        """
        from framework.runtime.qt_executor import QtTaskExecutor
        repo = TaskRepository()
        executor = QtTaskExecutor(repo=repo)
        return cls(executor=executor, repo=repo)

    @classmethod
    def cli(cls) -> "FrameworkContext":
        """Bootstrap the CLI / headless runtime.

        Creates a TaskRepository and CLITaskExecutor (synchronous).
        """
        from framework.runtime.cli_executor import CLITaskExecutor
        repo = TaskRepository()
        executor = CLITaskExecutor(repo=repo)
        return cls(executor=executor, repo=repo)

    # ------------------------------------------------------------------
    # Fluent registration API
    # ------------------------------------------------------------------

    def register(self, view_cls: Type, presenter_cls: Type) -> "FrameworkContext":
        """Register a view-presenter pair.

        Returns self so calls can be chained::

            ctx.register(ViewA, PresenterA).register(ViewB, PresenterB)
        """
        self.presenter_factory.register(view_cls, presenter_cls)
        return self

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def wire(self, view: Any) -> Tuple[Any, Any]:
        """Create and fully bind the registered presenter for *view*.

        This is the canonical "last mile" of dependency injection:
        the presenter gets the executor injected, then is bound to the view.

        Returns:
            ``(view, presenter)`` — both fully wired and ready to show.

        Example::

            view, presenter = ctx.wire(DemoView())
            view.show()

            # If you don't need the presenter reference:
            view, _ = ctx.wire(DemoView())
        """
        presenter = self.presenter_factory.create(view, self.executor)
        presenter.bind(view)
        return view, presenter
