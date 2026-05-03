# SDD — Module `framework.bootstrap`

**Module:** `framework/bootstrap.py`
**Type:** Composition Root / DI Container
**Dependencies:** `framework.core`, `framework.runtime`, `framework.ui`

---

## 1. Responsibility

`FrameworkContext` is the **Single Point of Wiring** for the entire application. It creates and owns all shared services (`TaskExecutor`, `TaskRepository`, `PresenterFactory`) in one place, and provides a fluent API to register and wire Views with Presenters. No application code should ever manually instantiate these services.

---

## 2. Class Diagram

```mermaid
classDiagram
    class FrameworkContext {
        +TaskExecutor executor
        +TaskRepository repo
        +PresenterFactory presenter_factory
        +classmethod qt() FrameworkContext
        +classmethod cli() FrameworkContext
        +register(view_cls, presenter_cls) FrameworkContext
        +wire(view) Tuple[view, presenter]
    }

    class TaskRepository {
        <<framework.core>>
    }

    class PresenterFactory {
        <<framework.ui>>
    }

    class QtTaskExecutor {
        <<framework.runtime>>
    }

    class CLITaskExecutor {
        <<framework.runtime>>
    }

    FrameworkContext *-- TaskRepository : owns
    FrameworkContext *-- PresenterFactory : owns
    FrameworkContext *-- QtTaskExecutor : owns (Qt mode)
    FrameworkContext *-- CLITaskExecutor : owns (CLI mode)
```

---

## 3. The 3-Step Composition Root Pattern

Every `App.run()` method follows exactly this ritual:

```python
# Step 1 — Bootstrap: one call, all services created
ctx = FrameworkContext.qt()

# Step 2 — Register: declare view → presenter mappings
ctx.register(MyView, MyPresenter)
# Chainable: ctx.register(ViewA, PresenterA).register(ViewB, PresenterB)

# Step 3 — Wire: instantiate view + create + bind presenter
view, _ = ctx.wire(MyView())
view.show()
```

---

## 4. Bootstrap Sequence

```mermaid
sequenceDiagram
    participant App as App.run()
    participant Ctx as FrameworkContext
    participant Repo as TaskRepository
    participant Exec as QtTaskExecutor
    participant Factory as PresenterFactory

    App->>Ctx: FrameworkContext.qt()
    activate Ctx
    Ctx->>Repo: TaskRepository()
    Ctx->>Exec: QtTaskExecutor(repo=repo)
    Ctx->>Factory: PresenterFactory()
    Ctx-->>App: return FrameworkContext instance
    deactivate Ctx

    App->>Ctx: register(MyView, MyPresenter)
    Ctx->>Factory: factory.register(MyView, MyPresenter)
    Ctx-->>App: return self [fluent]

    App->>Ctx: wire(MyView())
    activate Ctx
    Ctx->>Factory: factory.create(view, executor)
    Factory-->>Ctx: MyPresenter(executor)
    Ctx->>Ctx: presenter.bind(view)
    Ctx-->>App: return (view, presenter)
    deactivate Ctx

    App->>App: view.show()
```

---

## 5. Runtime Factory Methods

```mermaid
flowchart LR
    A([FrameworkContext]) --> B{Which runtime?}
    B -->|".qt()"| C["QtTaskExecutor + QThreadPool"]
    B -->|".cli()"| D["CLITaskExecutor + synchronous"]
    C --> E[FrameworkContext instance]
    D --> E
```

| Method | Creates | Use case |
|---|---|---|
| `FrameworkContext.qt()` | `QtTaskExecutor` backed by `QThreadPool` | PySide6 GUI applications |
| `FrameworkContext.cli()` | `CLITaskExecutor` synchronous | Terminal scripts, headless testing |

**Extension pattern:** To add a new runtime, add a classmethod:
```python
@classmethod
def ws(cls) -> "FrameworkContext":
    from framework.runtime.ws_executor import WebSocketTaskExecutor
    repo = TaskRepository()
    return cls(executor=WebSocketTaskExecutor(repo=repo), repo=repo)
```

---

## 6. `wire()` Internal Flow

```mermaid
flowchart TD
    A["wire(view_instance)"] --> B["factory.create(view, executor)"]
    B --> C{view type registered?}
    C -->|No| D[Raise KeyError with helpful message]
    C -->|Yes| E["presenter_cls(executor) — inject executor"]
    E --> F["presenter.bind(view)"]
    F --> G["return (view, presenter)"]
```

`wire()` is a convenience method that combines what would otherwise be three separate calls:
```python
# Manual equivalent of ctx.wire(view)
presenter = factory.create(view, executor)
presenter.bind(view)
view._set_presenter(presenter)   # handled inside bind()
```

---

## 7. Ownership & Lifetime Rules

```mermaid
flowchart LR
    subgraph FrameworkContext [FrameworkContext owns]
        R[TaskRepository]
        E[TaskExecutor]
        F[PresenterFactory]
    end

    subgraph App [App.run owns]
        QA[QApplication]
        V[View instances]
        P[Presenter instances]
    end

    P -->|injects executor from| FrameworkContext
    V -->|registered in| FrameworkContext
```

**Rules:**
1. Create `FrameworkContext` **once** per application lifecycle, inside `App.run()`.
2. **Never** instantiate `TaskExecutor`, `TaskRepository`, or `PresenterFactory` outside of `FrameworkContext`.
3. `FrameworkContext` must be created **after** `QApplication` (Qt mode) since `QtTaskExecutor` uses `QThreadPool.globalInstance()` which requires an active `QApplication`.

---

## 8. Testing Notes

| Scenario | Test approach |
|---|---|
| `FrameworkContext.cli()` | Pure pytest — create, register, wire with MagicMock view |
| `FrameworkContext.qt()` | Requires `QApplication`; use `pytest-qt` |
| `register()` chain | Register multiple pairs; verify all in factory |
| `wire()` with unregistered view | Assert `KeyError` raised |
| `wire()` binds presenter | Assert `presenter.view is view` after `wire()` |
