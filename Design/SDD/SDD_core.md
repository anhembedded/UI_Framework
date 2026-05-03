# SDD — Module `framework.core`

**Module:** `framework/core/`
**Type:** Pure Domain Layer
**Dependencies:** Python Standard Library only (no Qt, no PySide6)

---

## 1. Responsibility

This module is the **heart of the framework**. It defines the abstract contracts (interfaces) and data structures that the entire system depends on. The core must remain 100% pure Python — any file in this module that imports Qt is a defect.

---

## 2. Module Class Diagram

```mermaid
classDiagram
    class Task {
        <<Abstract>>
        +run(ctx: TaskContext) Any*
    }

    class TaskContext {
        <<Abstract>>
        +report_progress(value: int)*
        +report_message(msg: str)*
        +log(msg: str)*
        +is_cancelled() bool*
        +cancel()*
    }

    class TaskHandle {
        +cancel()
        +subscribe(callback)
        +get_state() TaskState
    }

    class TaskExecutor {
        <<Abstract>>
        +submit(task: Task) TaskHandle*
    }

    class TaskStatus {
        <<Enum>>
        PENDING
        RUNNING
        COMPLETED
        FAILED
        CANCELLED
    }

    class TaskState {
        <<ThreadSafe DataClass>>
        +str id
        +TaskStatus status
        +int progress
        +Any result
        +Optional~str~ error
        -Lock _lock
        +snapshot() TaskState
        +set_status(TaskStatus)
        +set_result(Any)
        +set_error(str)
        +set_progress(int)
    }

    class TaskRepository {
        -Dict _tasks
        +add(state: TaskState)
        +update(state: TaskState)
        +get(task_id: str) TaskState
        +all() Dict
    }

    class TaskFactory {
        <<Abstract>>
        +create() Task*
    }

    class TaskRegistry {
        -Dict _map
        +register(task_type, factory)
        +create(task_type, args) Task
    }

    class WithTimeout {
        -Task _task
        -float _timeout
        +run(ctx: TaskContext) Any
    }

    Task ..> TaskContext : uses
    TaskExecutor ..> Task : submits
    TaskExecutor ..> TaskHandle : returns
    TaskExecutor --> TaskRepository : updates state
    TaskState --> TaskStatus : has status
    WithTimeout --|> Task : extends
    WithTimeout o-- Task : wraps
    TaskRegistry --> TaskFactory : invokes
```

---

## 3. Component Specifications

### 3.1 `task.py` — `Task` ABC

**File:** `framework/core/task.py`

The root abstract class for all domain logic. A `Task` knows nothing about threads, Qt, or the UI.

```python
class Task(ABC):
    @abstractmethod
    def run(self, ctx: TaskContext) -> Any: ...
```

**Contract rules:**
- Must never import PySide6 or any UI library.
- Must call `ctx.is_cancelled()` at least once per loop iteration.
- Returns a value on success; raises on unrecoverable failure.
- Exceptions are caught by the Executor → `TaskState.status = FAILED`.

---

### 3.2 `task_context.py` — `TaskContext` ABC

**File:** `framework/core/task_context.py`

The communication port between a running Task and its hosting runtime. Tasks call these methods; the runtime adapters implement them.

| Method | Purpose | Notes |
|---|---|---|
| `report_progress(int)` | Progress 0–100 | Qt → Signal; CLI → print |
| `report_message(str)` | User-visible status | Qt → Signal; CLI → print |
| `log(str)` | Debug diagnostics | Routes to Python `logging`, NOT UI |
| `is_cancelled() → bool` | Check cancellation flag | Called in task loop |
| `cancel()` | Set cancellation flag | Called by `WithTimeout` or `TaskHandle` |

**Key design decision:** `log()` is explicitly separate from `report_message()`. Mixing them would flood the UI with debug noise. `log()` goes to Python's logging infrastructure (file, stderr) while `report_message()` goes to the status label visible to the end user.

---

### 3.3 `task_state.py` — `TaskState` & `TaskStatus`

**File:** `framework/core/task_state.py`

Thread-safe state object. Written by the Worker Thread, read by the GUI Thread.

```mermaid
stateDiagram-v2
    [*] --> PENDING : TaskState created
    PENDING --> RUNNING : Executor starts task
    RUNNING --> COMPLETED : task.run() returns
    RUNNING --> FAILED : task.run() raises
    RUNNING --> CANCELLED : ctx.is_cancelled() == True
    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

**Thread-safety mechanism:**
- All mutations (`set_status`, `set_result`, `set_error`, `set_progress`) acquire `_lock` before writing.
- `snapshot()` acquires the lock and returns `copy.copy(self)` — a shallow copy safe to read from any thread.
- GUI Thread must ONLY read via `handle.get_state()` which calls `state.snapshot()`.

---

### 3.4 `task_executor.py` — `TaskExecutor` ABC + `TaskHandle`

**File:** `framework/core/task_executor.py`

```mermaid
classDiagram
    class TaskExecutor {
        <<Abstract>>
        +submit(task: Task) TaskHandle*
    }
    class TaskHandle {
        +cancel()
        +subscribe(callback)
        +subscribe_message(callback)
        +subscribe_finished(callback)
        +subscribe_error(callback)
        +get_state() TaskState
    }
    TaskExecutor ..> TaskHandle : creates
```

`TaskHandle` is the returned token from `submit()`. The Presenter holds this handle to:
- Subscribe callbacks to signals (progress, finished, error).
- Cancel the task (`handle.cancel()`).
- Read the current state (`handle.get_state()`).

---

### 3.5 `task_repository.py` — `TaskRepository`

**File:** `framework/core/task_repository.py`

An in-memory dictionary store keyed by `TaskState.id`. It acts as the single source of truth for all submitted task states.

```mermaid
sequenceDiagram
    participant Executor
    participant Repo as TaskRepository
    participant Presenter

    Executor->>Repo: add(state) on submit
    Executor->>Repo: update(state) on status change
    Presenter->>Repo: get(task_id) (optional query)
```

**Note:** In the current architecture, Presenters receive state updates via `TaskHandle` subscriptions (Signals). Direct `TaskRepository` queries are optional and intended for future features (e.g., task dashboards, audit logs).

---

### 3.6 `task_registry.py` — `TaskRegistry` + `TaskFactory`

**File:** `framework/core/task_registry.py`

A lookup table mapping task type keys to factory callables. Used when tasks need to be created dynamically by type name (e.g., from a configuration file or a command string).

```python
registry = TaskRegistry()
registry.register("scan", lambda **kw: FileScanTask(**kw))
task = registry.create("scan", directory="/tmp")
```

`TaskFactory` ABC provides a typed interface for object-based factories:

```python
class ScanTaskFactory(TaskFactory):
    def create(self) -> FileScanTask:
        return FileScanTask(directory="/tmp")
```

---

### 3.7 `task_timeout.py` — `WithTimeout`

**File:** `framework/core/task_timeout.py`

A Decorator-pattern `Task` that wraps any existing task and enforces a maximum execution time.

```mermaid
sequenceDiagram
    participant Executor
    participant WithTimeout
    participant Timer as threading.Timer
    participant InnerTask as Wrapped Task
    participant Ctx as TaskContext

    Executor->>WithTimeout: run(ctx)
    WithTimeout->>Timer: start(timeout, ctx.cancel)
    WithTimeout->>InnerTask: run(ctx)
    note over InnerTask: Task runs normally...

    alt Timeout fires before task finishes
        Timer->>Ctx: cancel()
        InnerTask->>Ctx: is_cancelled() == True
        InnerTask-->>WithTimeout: return None
    else Task finishes within timeout
        InnerTask-->>WithTimeout: return result
    end

    WithTimeout->>Timer: cancel() (always)
    WithTimeout-->>Executor: return result
```

**Usage:**
```python
task = WithTimeout(HeavyTask(), timeout_sec=30.0)
handle = executor.submit(task)
```

The wrapped task is responsible for checking `ctx.is_cancelled()` and returning early — cooperative cancellation applies.

---

## 4. Data Flow Summary

```mermaid
flowchart LR
    A([App creates Task]) --> B[TaskExecutor.submit]
    B --> C{Runtime?}
    C -->|Qt| D[QtTaskRunner runs task.run on Worker Thread]
    C -->|CLI| E[CLITaskExecutor runs task.run on Main Thread]
    D --> F[ctx.report_progress → Qt Signal]
    E --> G[ctx.report_progress → print stdout]
    F --> H[Presenter callback on GUI Thread]
    G --> I[Result available after submit returns]
    H --> J[View updated]
```

---

## 5. Testing Notes

All components in `framework/core` are testable with **pure pytest** — no Qt required.

| Component | Test approach |
|---|---|
| `TaskState` | Direct mutation + `snapshot()` assertion |
| `TaskRepository` | Add/get/update with `TaskState` stubs |
| `WithTimeout` | CLITaskContext with cancellation check |
| `TaskRegistry` | Register factory lambda + create |
| `Task` subclass | Run with `CLITaskContext`, assert result |
