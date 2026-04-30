"""PresenterFactory — lookup table for view-to-presenter mapping.

Design:
    - The factory is a PURE registry. It does NOT store the executor.
    - The executor is injected at ``create()`` time (not at registration time).
    - This decouples the registration phase from the runtime phase, making it
      possible to register all view-presenter pairs before the executor exists.
"""

from __future__ import annotations

from typing import Any, Dict, Type

from ui.presenters.base_presenter import BasePresenter


class PresenterFactory:
    """Maps view classes to their corresponding presenter classes.

    Usage::

        factory = PresenterFactory()
        factory.register(MyView, MyPresenter)
        presenter = factory.create(my_view_instance, executor)
    """

    def __init__(self) -> None:
        self._mapping: Dict[Type, Type[BasePresenter]] = {}

    def register(self, view_cls: Type, presenter_cls: Type[BasePresenter]) -> None:
        """Register a view class → presenter class mapping."""
        self._mapping[view_cls] = presenter_cls

    def create(self, view: Any, executor) -> BasePresenter:
        """Instantiate and return the presenter registered for *view*'s type.

        Args:
            view:     The view instance to look up.
            executor: The TaskExecutor to inject into the presenter.

        Raises:
            KeyError: If no presenter is registered for this view type.
        """
        view_cls = type(view)
        if view_cls not in self._mapping:
            raise KeyError(
                f"No presenter registered for view type '{view_cls.__name__}'. "
                f"Call factory.register({view_cls.__name__}, YourPresenter) first."
            )
        presenter_cls = self._mapping[view_cls]
        return presenter_cls(executor)
