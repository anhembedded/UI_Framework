# Software Design Document (SDD)

## Project: Task-Oriented UI Framework (PySide6 + CLI)

---

# 1. Overview

## 1.1 Purpose

Framework này cung cấp một nền tảng để xây dựng ứng dụng desktop (PySide6) và CLI dựa trên **task execution model**, với mục tiêu:

* Tách biệt hoàn toàn Domain logic khỏi UI
* Hỗ trợ đa luồng an toàn (GUI không bị block)
* Cho phép reuse domain cho cả GUI và CLI
* Dễ test, dễ mở rộng

---

## 1.2 Design Goals

* Loose coupling giữa: Domain, UI, Runtime (threading)
* Không phụ thuộc Qt trong Domain
* Hỗ trợ Dependency Injection (Manual, Composition Root)
* Không "magic binding" quá mức
* API rõ ràng, predictable
* View Lifecycle management (cleanup khi đóng cửa sổ)
* Thread-safe state mutations

---

## 1.3 Non-Goals

* Không build full DI container
* Không ép buộc UI pattern (MVP/MVVM)
* Không quản lý lifecycle của QWidget ngoài BaseQtView

---

# 2. High-Level Architecture

```
+----------------------+
|    Entry Point       |
|   main.py            |
|   AppFactory         |
+----------+-----------+
           |
           v
+----------------------+
|  Application Layer   |
|  BaseApp / QtApp     |
|  CLIApp              |
+----------+-----------+
           |
           v
+----------------------+
|   UI Layer           |
|  BaseQtView          |
|  BasePresenter       |
|  PresenterFactory    |
+----------+-----------+
           |
           v
+----------------------+
|  Framework Core      |
|  Task + TaskContext  |
|  TaskExecutor        |
|  TaskState (locked)  |
|  TaskRepository      |
|  TaskRegistry        |
|  WithTimeout         |
+----------+-----------+
           |
           v
+----------+-----------+
|  Adapters / Runtime  |
|  Qt: QThreadPool     |
|  CLI: synchronous    |
+----------+-----------+
           |
           v
+----------------------+
|  Apps (Domain)       |
|  demo_basic          |
|  demo_multi_task     |
|  demo_file_processor |
+----------------------+
```

---

# 3. Core Concepts

## 3.1 Task

```python
class Task(ABC):
    def run(self, ctx: TaskContext) -> Any: ...
```

* Pure domain logic, zero Qt/UI dependency
* Checks `ctx.is_cancelled()` for cooperative cancellation

---

## 3.2 TaskContext (ABC)

```python
class TaskContext(ABC):
    def report_progress(self, value: int): ...
    def report_message(self, message: str): ...
    def log(self, message: str): ...          # → Python logging, NOT mixed with UI messages
    def is_cancelled(self) -> bool: ...
    def cancel(self) -> None: ...             # callable externally (e.g. WithTimeout)
```

* Full ABC — missing any method raises `TypeError` at instantiation
* `log()` is separated from `report_message()` to avoid mixing UI messages with diagnostics

---

## 3.3 TaskState (Thread-Safe)

```python
@dataclass
class TaskState:
    id: str
    status: TaskStatus
    progress: int
    result: Any
    error: Optional[str]
    _lock: threading.Lock

    def snapshot() -> TaskState: ...     # safe read from any thread
    def set_status(status): ...          # locked write
    def set_result(result): ...          # locked write
    def set_error(error): ...            # locked write
```

* All mutations go through locked setters — no raw attribute assignment from worker thread
* `snapshot()` returns a shallow copy for safe GUI-thread reads

---

## 3.4 TaskStatus

```python
class TaskStatus(Enum):
    PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
```

---

## 3.5 TaskHandle

```python
class TaskHandle:
    def cancel(): ...
    def subscribe(callback): ...              # progress signal
    def subscribe_message(callback): ...
    def subscribe_finished(callback): ...
    def subscribe_error(callback): ...
    def get_state() -> TaskState: ...        # returns snapshot()
```

* Qt: callbacks fire on GUI thread via queued signal connections
* CLI: `subscribe()` raises `UserWarning` (no async notifications in sync mode)

---

## 3.6 WithTimeout (P2)

```python
class WithTimeout(Task):
    def __init__(self, task: Task, timeout_sec: float): ...
```

* Wraps any Task; starts a `threading.Timer` that calls `ctx.cancel()` on expiry
* Works with both Qt and CLI runtimes

---

# 4. Framework Core

## 4.1 TaskExecutor

```python
class TaskExecutor(ABC):
    def submit(self, task: Task) -> TaskHandle: ...
```

---

## 4.2 TaskRepository

```python
class TaskRepository:
    def add(state: TaskState): ...
    def update(state: TaskState): ...
    def get(task_id: str) -> TaskState: ...
    def all() -> Dict: ...
```

---

## 4.3 TaskRegistry + TaskFactory

```python
class TaskFactory(ABC):
    def create() -> Task: ...

class TaskRegistry:
    def register(task_type, factory): ...
    def create(task_type, *args, **kwargs) -> Task: ...
```

---

# 5. Runtime Layer

## 5.1 Qt Implementation (`QtTaskExecutor`)

* `QThreadPool.globalInstance()` — shares the global thread pool
* Each submission creates a `QtTaskRunner(QRunnable)` + `QtTaskContext`
* `QtTaskContext` emits Qt signals (progress, message, error, finished)
* Signals queued → automatically dispatched to GUI thread

## 5.2 CLI Implementation (`CLITaskExecutor`)

* Synchronous — runs task in calling thread, blocks until done
* `CLITaskContext.log()` routes to **Python `logging` module** (DEBUG level) — NOT `print()` (P1 fix)
* `CLITaskContext.report_message()` and `report_progress()` use `print()`
* `CLITaskHandle.subscribe()` raises `UserWarning` (P0 fix — was a silent no-op)

---

# 6. UI Layer

## 6.1 BaseQtView

```python
class BaseQtView(QWidget):
    def _set_presenter(presenter): ...
    def closeEvent(event: QCloseEvent): ...   # calls presenter.cleanup()
```

* Owns a reference to its Presenter
* Triggers cleanup on `closeEvent` (user closes window)

## 6.2 BasePresenter

```python
class BasePresenter:
    executor: TaskExecutor
    view: Any
    _handles: List[TaskHandle]           # P1: multi-handle tracking

    def bind(view): ...                  # registers destroyed signal
    def cleanup(): ...                   # cancels ALL handles, drops refs
    def _track(handle): ...              # add to handles list
    def _untrack(handle): ...            # remove completed handle

    @property
    def is_alive() -> bool: ...          # P0: null-check guard for callbacks
```

* P0: All subclass callbacks MUST guard with `if not self.is_alive: return`
* P1: Tracks multiple concurrent handles — cleanup() cancels all of them
* Auto-cleanup via Qt `destroyed` signal as a secondary safety net

## 6.3 PresenterFactory

```python
class PresenterFactory:
    def register(view_cls, presenter_cls): ...
    def create(view, executor) -> BasePresenter: ...   # executor injected here, not stored
```

* Pure lookup table — does NOT store the executor (decoupled)

---

# 7. Application Layer

## 7.1 AppFactory

```python
class AppFactory:
    _REGISTRY = {
        "basic": (QtDemoBasicApp, CLIDemoBasicApp),
        "multi": (QtDemoMultiTaskApp, CLIDemoMultiTaskApp),
        "files": (QtDemoFileProcessorApp, CLIDemoFileProcessorApp),
    }

    @classmethod
    def from_args(argv) -> BaseApp: ...
```

* Reads `--app=<name>` and `--cli` flags
* Initialises logging + global exception handler before returning the app
* Easily extended: add a tuple to `_REGISTRY`

## 7.2 Logging Setup (P1/P2)

```python
setup_logging(level, log_file)       # configures root logger + optional rotating file
setup_exception_handler()            # installs sys.excepthook
```

---

# 7b. FrameworkContext — Single Point of Wiring

`framework/bootstrap.py` is the **Lightweight DI Container** for the application layer.
It eliminates DI scatter across App classes and creates all framework services in ONE place.

```python
class FrameworkContext:
    executor:           TaskExecutor      # owned here, injected into presenters
    repo:               TaskRepository   # owned here, passed to executor
    presenter_factory:  PresenterFactory # owned here, used by wire()

    @classmethod
    def qt()  -> FrameworkContext: ...   # creates QtTaskExecutor + repo

    @classmethod
    def cli() -> FrameworkContext: ...   # creates CLITaskExecutor + repo

    def register(view_cls, presenter_cls) -> self: ...  # fluent, chainable
    def wire(view) -> (view, presenter): ...            # create + bind in one call
```

**3-step Composition Root pattern** (every `BaseApp.run()` follows this):

```python
ctx = FrameworkContext.qt()            # 1. Bootstrap ALL services
ctx.register(MyView, MyPresenter)      # 2. Declare view-presenter pairs
view, _ = ctx.wire(MyView())           # 3. Inject + bind → ready to show
view.show()
```

**Rules:**
* Create ONCE per application lifecycle
* NEVER instantiate `TaskExecutor` or `TaskRepository` outside `FrameworkContext`
* Adding a new runtime = one new classmethod in `FrameworkContext`

---

# 8. Data Flow

```
User Action
    ↓
Presenter.on_xxx()
    ↓
executor.submit(task)              → returns TaskHandle
    ↓ (Qt: QThreadPool worker thread)
Task.run(ctx)
    ↓
ctx.report_progress / report_message / log
    ↓ (Qt: queued signal → GUI thread)
Presenter callback (is_alive guarded)
    ↓
View.set_xxx()
```

---

# 9. Threading Model

| Runtime | Mechanism | Thread Safety |
|---|---|---|
| Qt | QThreadPool + QRunnable + queued signals | ✅ Signals dispatched to GUI thread |
| CLI | Synchronous, calling thread | ✅ No concurrency |
| State mutations | `threading.Lock` in TaskState | ✅ Locked setters |
| Cancellation | `_cancelled` bool flag | ✅ Atomic on CPython |

---

# 9b. Testing Strategy

## 9b.1 Test Layout

```
tests/
├── conftest.py              shared fixtures + task stubs (real implementations)
├── framework/
│   ├── core/               test_task_state, test_task_context, test_task_repository, test_task_timeout
│   ├── runtime/            test_cli_executor
│   └── adapters/           test_cli_context
├── ui/                     test_base_presenter, test_presenter_factory
└── bootstrap/              test_framework_context
```

## 9b.2 Design Principles

| Criterion | Implementation |
|---|---|
| **Protection against regressions** | All public API paths covered including edge cases and error states |
| **Resistance to refactoring** | Tests assert on BEHAVIOUR (state values, return types, exception types), NEVER on private attributes or internal data structures |
| **Fast feedback** | No Qt required for fast tests. Markers: `qt` and `slow`. Run `pytest -m 'not qt and not slow'` in < 3 s. |
| **Maintainability** | AAA pattern, one behaviour per test, descriptive names (`test_<unit>_<scenario>_<expected>`) |

## 9b.3 Test Runner

```powershell
.\run_tests.ps1 -Fast                  # development — no Qt/sleep
.\run_tests.ps1 -Coverage              # + term-missing coverage
.\run_tests.ps1 -Html                  # + HTML report in htmlcov/
.\run_tests.ps1 -Module framework/core # specific module only
.\run_tests.ps1 -Filter cleanup        # -k keyword filter
.\run_tests.ps1 -FailFast              # stop at first failure
```

## 9b.4 Mock Policy

* **Task stubs** = real `Task` subclasses (not mocks) — preserves contract integrity
* **View** = `MagicMock` — only at presenter/UI boundary
* **Qt signals** = not tested directly (requires QApplication) — marked `qt`
* **Private attributes** = NEVER accessed in tests

---

# 10. View Lifecycle

```
Window Created
    ↓
presenter.bind(view)            → connects destroyed signal
view._set_presenter(presenter)  → view holds presenter ref
    ↓
[Task runs, signals fire]
    ↓
User closes window
    ↓
BaseQtView.closeEvent()
    ↓
presenter.cleanup()             → cancel all handles, view = None
view._presenter = None          → break cycle
super().closeEvent()            → Qt closes window
    ↓
(optional) view.destroyed signal → _on_view_destroyed() as safety net
```

---

# 11. Project Structure

```
UI_FrameworkDev/
├── main.py                          # 3-line entry point
├── pyproject.toml
├── .gitignore
│
├── framework/                       # Core framework (no Qt in core/)
│   ├── core/
│   │   ├── task.py                  # Task ABC
│   │   ├── task_context.py          # TaskContext ABC (incl. cancel())
│   │   ├── task_state.py            # TaskState + threading.Lock
│   │   ├── task_executor.py         # TaskExecutor ABC + TaskHandle base
│   │   ├── task_repository.py       # In-memory state store
│   │   ├── task_registry.py         # TaskRegistry + TaskFactory ABC
│   │   └── task_timeout.py          # WithTimeout decorator task
│   ├── runtime/
│   │   ├── qt_executor.py           # QtTaskExecutor / QtTaskHandle / QtTaskRunner
│   │   └── cli_executor.py          # CLITaskExecutor / CLITaskHandle
│   ├── adapters/
│   │   ├── qt/qt_context.py         # QtTaskContext → Qt signals
│   │   └── cli/cli_context.py       # CLITaskContext → stdout
│   └── logging_setup.py             # setup_logging() + setup_exception_handler()
│
├── ui/                              # Framework UI base classes only
│   ├── views/
│   │   └── base_qt_view.py          # BaseQtView (closeEvent lifecycle)
│   └── presenters/
│       ├── base_presenter.py        # BasePresenter (is_alive, _handles, cleanup)
│       └── presenter_factory.py     # PresenterFactory (decoupled from executor)
│
├── app/                             # Composition root
│   ├── __init__.py
│   └── app_factory.py               # AppFactory + BaseApp + QtApp/CLIApp per demo
│
├── apps/                            # Demo applications
│   ├── demo_basic/                  # Simple 5-step progress task
│   │   ├── tasks/demo_task.py
│   │   ├── views/demo_view.py
│   │   └── presenters/demo_presenter.py
│   ├── demo_multi_task/             # Parallel task runner with dynamic cards
│   │   ├── tasks/work_task.py
│   │   ├── views/multi_task_view.py
│   │   └── presenters/multi_task_presenter.py
│   └── demo_file_processor/         # File scanner with 30s timeout
│       ├── tasks/file_scan_task.py
│       ├── views/file_processor_view.py
│       └── presenters/file_processor_presenter.py
│
└── Design/                          # Architecture documentation
    ├── Software Design Document.md
    ├── Architecture_Tutorial.md
    ├── Class_Diagram.puml
    ├── Sequence_Diagram.puml
    └── Sequence_Diagram_CLI Flow.puml
```

---

# 12. Acceptance Criteria

* ✅ Domain task chạy được không cần Qt
* ✅ GUI và CLI dùng chung task
* ✅ Presenter test được độc lập (inject mock executor)
* ✅ Không circular dependency
* ✅ Không UI reference trong core
* ✅ Cleanup khi đóng cửa sổ (không zombie task)
* ✅ Thread-safe state mutations
* ✅ Global exception handler
* ✅ Logging với rotating file handler
* ✅ Task timeout via WithTimeout

---

# 13. Future Extensions

* DI Container (auto-wiring)
* Event Bus (pub-sub cross-component)
* Router / Window Manager
* Reactive Data Binding (MVVM)
* Task retry policy & DAG dependencies
* Metrics / tracing
* i18n / Localization
