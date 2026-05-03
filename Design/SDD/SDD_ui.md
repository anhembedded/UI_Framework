# SDD — Module `framework.ui`

**Module:** `framework/ui/`
**Sub-modules:** `ui/views/`, `ui/presenters/`
**Type:** UI Contract Layer
**Dependencies:** `framework.core`, PySide6 (`BaseQtView` only)

---

## 1. Responsibility

This module defines the **mandatory base classes** for all application Views and Presenters. It enforces the lifecycle contract that prevents zombie tasks and `NoneType` crashes. Application code inherits from these classes — it never imports PySide6's `QWidget` directly.

---

## 2. Module Class Diagram

```mermaid
classDiagram
    class BaseQtView {
        <<QWidget>>
        -BasePresenter _presenter
        +_set_presenter(presenter)
        +closeEvent(event: QCloseEvent)
    }

    class BasePresenter {
        +TaskExecutor executor
        +Any view
        -List _handles
        -Logger _logger
        +bind(view)
        +cleanup()
        +_track(handle)
        +_untrack(handle)
        +_on_view_destroyed()
        +is_alive: bool
    }

    class PresenterFactory {
        -Dict _mapping
        +register(view_cls, presenter_cls)
        +create(view, executor) BasePresenter
    }

    class ConcreteView {
        <<Application Code>>
        +set_progress(int)
        +set_message(str)
        +set_finished(status)
    }

    class ConcretePresenter {
        <<Application Code>>
        +bind(view)
        +on_start()
        +on_progress(int)
        +on_finished(status, handle)
    }

    BaseQtView <|-- ConcreteView : inherits
    BasePresenter <|-- ConcretePresenter : inherits
    BaseQtView --> BasePresenter : calls cleanup()
    PresenterFactory ..> BasePresenter : creates
    ConcretePresenter --> ConcreteView : updates via set_xxx()
```

---

## 3. Component Specifications

### 3.1 `views/base_qt_view.py` — `BaseQtView`

**File:** `framework/ui/views/base_qt_view.py`

The foundational `QWidget` subclass that every application view must inherit. Its sole added behavior is the `closeEvent` override.

```mermaid
sequenceDiagram
    actor User
    participant OS
    participant BaseQtView
    participant Presenter as BasePresenter

    User->>OS: Click [X] button
    OS->>BaseQtView: closeEvent(QCloseEvent)
    BaseQtView->>BaseQtView: Check _presenter is not None
    BaseQtView->>Presenter: _presenter.cleanup()
    Presenter->>Presenter: cancel all _handles
    Presenter->>Presenter: self.view = None
    BaseQtView->>BaseQtView: self._presenter = None
    BaseQtView->>OS: super().closeEvent(event) — window closes
```

**Contract:**
- Every application view MUST inherit `BaseQtView`, not `QWidget`.
- After `PresenterFactory.create()`, call `view._set_presenter(presenter)` to wire the lifecycle.

**What happens WITHOUT `BaseQtView`:**
If a view inherits raw `QWidget` and the user closes the window while a background task runs, the `QWidget` is destroyed. The background thread later emits a signal, the connected slot fires, tries to access `self.view.set_progress()`, and crashes with `RuntimeError: Internal C++ object (QProgressBar) already deleted`.

---

### 3.2 `presenters/base_presenter.py` — `BasePresenter`

**File:** `framework/ui/presenters/base_presenter.py`

The foundation for all presenters. Manages the Task lifecycle (handle tracking), thread safety (`is_alive`), and cleanup.

#### 3.2.1 Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Created : __init__(executor)
    Created --> Bound : bind(view) called
    Bound --> Active : task submitted, handle tracked
    Active --> Active : more tasks submitted
    Active --> Cleanup : cleanup() called OR view.destroyed fires
    Cleanup --> Dead : view = None, handles cleared
    Dead --> [*]
```

#### 3.2.2 Handle Tracking

```mermaid
flowchart LR
    A[executor.submit] --> B[returns handle]
    B --> C[_track handle]
    C --> D[_handles list]
    D --> E{Task finishes}
    E -->|on_finished| F[_untrack handle]
    E -->|window closes| G[cleanup]
    G --> H[cancel ALL handles in list]
    H --> I[_handles.clear]
```

Every `TaskHandle` returned from `executor.submit()` MUST be passed to `self._track(handle)`. Failure to track a handle means `cleanup()` cannot cancel it — the task becomes a zombie.

#### 3.2.3 The `is_alive` Guard

```mermaid
sequenceDiagram
    participant Worker as Worker Thread
    participant Ctx as QtTaskContext
    participant Queue as Qt Event Queue
    participant GUI as GUI Thread
    participant Presenter

    Worker->>Ctx: report_progress(90)
    Ctx->>Queue: enqueue signal

    note over Presenter: User closes window at this exact moment
    note over Presenter: cleanup() sets self.view = None

    Queue->>GUI: deliver signal
    GUI->>Presenter: on_progress(90) fires
    Presenter->>Presenter: if not self.is_alive: return
    note over Presenter: is_alive == False → silently drops event
    note over Presenter: NO CRASH
```

`is_alive` is a property that returns `self.view is not None`. After `cleanup()` sets `self.view = None`, any late-arriving signal hits the guard and returns silently.

**Rule:** Every presenter callback that touches `self.view` MUST begin with:
```python
def on_progress(self, value: int) -> None:
    if not self.is_alive:
        return
    self.view.set_progress(value)
```

#### 3.2.4 Dual Cleanup Safety Net

```mermaid
flowchart TD
    A([Window closed]) --> B[BaseQtView.closeEvent]
    B --> C[presenter.cleanup via _presenter ref]

    D([Qt destroys widget]) --> E[view.destroyed signal fires]
    E --> F[presenter._on_view_destroyed]
    F --> G{view is not None?}
    G -->|Yes| H[presenter.cleanup]
    G -->|No| I[Already cleaned — skip]

    C --> J[is_alive = False, handles cancelled]
    H --> J
```

`cleanup()` is **idempotent** — calling it twice is safe. The second call finds `_handles` already empty and `self.view` already `None`, and returns immediately.

---

### 3.3 `presenters/presenter_factory.py` — `PresenterFactory`

**File:** `framework/ui/presenters/presenter_factory.py`

A stateless registry mapping view classes to presenter classes. The executor is NOT stored in the factory — it is injected at `create()` time. This decouples the registration phase from the runtime execution phase.

```mermaid
classDiagram
    class PresenterFactory {
        -Dict~Type, Type~ _mapping
        +register(view_cls, presenter_cls)
        +create(view: Any, executor) BasePresenter
    }
    note for PresenterFactory "Executor is NOT stored here.\nIt is injected at create() time."
```

```mermaid
sequenceDiagram
    participant App as App.run()
    participant Factory as PresenterFactory
    participant Presenter as ConcretePresenter

    App->>Factory: register(MyView, MyPresenter)
    note over Factory: stores {MyView: MyPresenter} in _mapping

    App->>Factory: create(my_view_instance, executor)
    Factory->>Factory: presenter_cls = _mapping[type(my_view_instance)]
    Factory->>Presenter: MyPresenter(executor)
    Factory-->>App: return presenter instance
```

**Error case:** If `create()` is called with a view type that was not registered, a clear `KeyError` is raised with the view class name and a hint to call `register()`.

---

## 4. Full Lifecycle: Startup to Cleanup

```mermaid
sequenceDiagram
    participant App
    participant Factory as PresenterFactory
    participant View as BaseQtView subclass
    participant Presenter as BasePresenter subclass
    participant Executor

    App->>Factory: register(View, Presenter)
    App->>View: View()
    App->>Factory: create(view, executor)
    Factory->>Presenter: Presenter(executor)
    Factory-->>App: presenter
    App->>Presenter: bind(view)
    Presenter->>Presenter: self.view = view
    Presenter->>View: view.destroyed.connect(_on_view_destroyed)
    App->>View: _set_presenter(presenter)
    View->>View: self._presenter = presenter
    App->>View: show()

    note over View,Presenter: Application runs...

    actor User
    User->>View: click [X]
    View->>Presenter: closeEvent → cleanup()
    Presenter->>Presenter: cancel all handles
    Presenter->>Presenter: self.view = None
    View->>View: self._presenter = None
    View->>View: super().closeEvent()
```

---

## 5. Testing Notes

| Component | Test approach |
|---|---|
| `BasePresenter.bind()` | Pass `MagicMock` view; assert `self.view` set |
| `BasePresenter.cleanup()` | Call cleanup; assert `is_alive == False`, handles cancelled |
| `BasePresenter._track/_untrack` | Track stub handle; assert list size |
| `BasePresenter.is_alive` guard | Set `view = None`; call callback; assert no AttributeError |
| `PresenterFactory.create()` | Register pair; call create; assert returned type |
| `PresenterFactory.create() KeyError` | Unregistered view; assert `KeyError` raised |
| `BaseQtView.closeEvent` | Requires `pytest-qt`; verify `cleanup()` called |
