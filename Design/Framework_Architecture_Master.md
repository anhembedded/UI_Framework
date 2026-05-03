# Task-Oriented UI Framework — Architecture Master Document

This document details the overall architecture and the design of each module within the **Task-Oriented UI Framework**. The framework is designed strictly following **Clean Architecture** principles, achieving a complete separation of concerns between Business Logic (Domain/Task) and the User Interface (UI) through interfaces and a lightweight DI Container.

---

## 1. Overall Architecture

The framework applies a clear layered architectural model, ensuring the Dependency Inversion principle. The UI layer depends on the Core, and the Core is completely agnostic of the UI or any external libraries (including Qt).

```mermaid
graph TD
    subgraph APP [Application Layer]
        AppFactory[AppFactory]
        DemoApp[Concrete Apps / Demos]
    end

    subgraph FW_UI [Framework UI Layer]
        BaseQtView[BaseQtView]
        BasePresenter[BasePresenter]
        PresenterFactory[PresenterFactory]
    end

    subgraph FW_RUNTIME [Framework Runtime & Adapters]
        Bootstrap[FrameworkContext DI Container]
        QtExecutor[QtTaskExecutor]
        CLIExecutor[CLITaskExecutor]
        QtContext[QtTaskContext]
        CLIContext[CLITaskContext]
    end

    subgraph FW_CORE [Framework Core Layer - Pure Python]
        Task[Task ABC]
        TaskContext[TaskContext ABC]
        TaskExecutor[TaskExecutor ABC]
        TaskState[TaskState]
        TaskRepo[TaskRepository]
    end

    %% Dependencies
    DemoApp --> Bootstrap
    DemoApp --> FW_UI
    DemoApp --> Task
    
    FW_UI --> TaskExecutor
    FW_UI --> TaskState
    
    Bootstrap --> FW_RUNTIME
    Bootstrap --> FW_UI
    Bootstrap --> FW_CORE

    FW_RUNTIME -. implements .-> TaskExecutor
    FW_RUNTIME -. implements .-> TaskContext
    
```

---

## 2. Module Specifications

### 2.1. Module `framework.core`
The heart of the Framework. It is 100% Pure Python, completely independent of PyQt/PySide or the underlying OS.

```mermaid
classDiagram
    class Task {
        <<Abstract>>
        +run(ctx: TaskContext)* Any
    }
    
    class TaskContext {
        <<Abstract>>
        +report_progress(value: int)*
        +report_message(msg: str)*
        +log(msg: str)*
        +is_cancelled()* bool
        +cancel()*
    }
    
    class TaskExecutor {
        <<Abstract>>
        +submit(task: Task)* TaskHandle
    }
    
    class TaskState {
        <<ThreadSafe DataClass>>
        +str id
        +TaskStatus status
        +int progress
        +Any result
        +str error
        +snapshot() TaskState
        +set_status(...)
    }

    class TaskRepository {
        -dict storage
        +add(state: TaskState)
        +update(state: TaskState)
        +get(id: str) TaskState
    }

    Task ..> TaskContext : uses
    TaskExecutor ..> Task : runs
    TaskExecutor --> TaskRepository : updates
```

**Key Components:**
*   **`Task`**: Defines a specific unit of work. All business logic resides in the `run(ctx)` method.
*   **`TaskContext`**: Provides a safe communication channel for the Task to report progress, log info, or check the `cancel` flag without knowing whether it is running in a CLI or GUI environment.
*   **`TaskState`**: Stores the execution state of a Task. It contains an internal `threading.Lock` to ensure thread-safety when the Worker thread updates the state and the GUI thread reads it via the `snapshot()` method.

### 2.2. Modules `framework.runtime` & `framework.adapters`
The bridge (Adapters) that allows the Core to run in specific environments (Qt GUI or Command Line).

```mermaid
classDiagram
    class TaskExecutor { <<Interface>> }
    class TaskContext { <<Interface>> }
    
    class QtTaskExecutor {
        -QThreadPool pool
        +submit(task) QtTaskHandle
    }
    
    class CLITaskExecutor {
        +submit(task) CLITaskHandle
    }
    
    class QtTaskContext {
        +progress_updated: Signal
        +message_updated: Signal
        +report_progress()
        +report_message()
    }
    
    class CLITaskContext {
        +report_progress() -> print stdout
        +log() -> python logging
    }

    TaskExecutor <|-- QtTaskExecutor
    TaskExecutor <|-- CLITaskExecutor
    TaskContext <|-- QtTaskContext
    TaskContext <|-- CLITaskContext
    
    QtTaskExecutor ..> QtTaskContext : creates
    CLITaskExecutor ..> CLITaskContext : creates
```

*   **`QtTaskExecutor`**: Manages the `QThreadPool`. When it receives a `Task`, it wraps it in a `QRunnable` and executes it on a background worker thread.
*   **`QtTaskContext`**: Defines Qt Signals (`progress_updated`, `finished`, etc.). Any calls from the Task (on the Worker Thread) emit Signals safely routed to the GUI Thread (via Qt's Queued Connections).
*   **`CLITaskExecutor / CLITaskContext`**: A synchronous execution environment allowing developers to test Tasks via the Terminal instantly without launching a GUI.

### 2.3. Module `framework.ui` (View & Presenter Contracts)
Provides mandatory Base classes to standardize the UI flow and prevent memory leaks (Zombie Tasks).

```mermaid
graph LR
    subgraph UI [framework.ui]
        BaseQtView[BaseQtView]
        BasePresenter[BasePresenter]
        Factory[PresenterFactory]
    end

    BaseQtView -- _presenter.cleanup() --> BasePresenter
    BaseQtView -- closeEvent() --> BaseQtView
    Factory -- injects Executor --> BasePresenter
    BasePresenter -- cancels --> Handles[Task Handles]
    
    style BaseQtView fill:#e8f4f8,stroke:#17a2b8
    style BasePresenter fill:#e8f4f8,stroke:#17a2b8
```

*   **`BaseQtView`**: Inherits from `QWidget`. Overrides `closeEvent()` to automatically call `presenter.cleanup()` when the window is closed.
*   **`BasePresenter`**:
    *   Owns the safety guard `self.is_alive`. Any callback returning from a Thread to the UI **MUST** check `if not self.is_alive: return` to prevent `NoneType` crashes.
    *   Tracks all running Tasks via the `_handles` list.
    *   The `cleanup()` method automatically cascades the cancel signal to all active Tasks when the View is destroyed.

### 2.4. Module `framework.bootstrap` (Single Point of Wiring)
Acts as the DI (Dependency Injection) Container where all Framework dependencies are initialized and connected.

*   **`FrameworkContext`**: A highly lightweight DI Container. Provides a fluent API (`register()`, `wire()`) so that the `run()` method of any Application only requires exactly 3 lines of code to set up a complex configuration.

---

## 3. Application Startup Sequence

The following sequence diagram illustrates the lifecycle from launching the `main.py` entry point to fully displaying a wired Application View.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant View
    participant Presenter
    participant Executor as QtTaskExecutor
    participant Task as Domain Task (Worker Thread)
    participant Ctx as QtTaskContext (Signals)
    
    User->>View: Click "Start"
    View->>Presenter: on_start_clicked()
    
    Presenter->>Executor: submit(DomainTask)
    Executor->>Ctx: Create Context
    Executor->>Task: Run in QThreadPool
    Executor-->>Presenter: TaskHandle
    
    Presenter->>Presenter: _track(handle)
    Presenter->>TaskHandle: subscribe_progress(update_ui)
    
    note over Task, Ctx: Worker Thread
    loop Every step
        Task->>Ctx: report_progress()
        Ctx-->>View: Emit Signal (Queued)
        View->>Presenter: Callback (update_ui)
        Presenter->>Presenter: Check if is_alive
        Presenter->>View: view.set_progress()
    end
    
    Task-->>Executor: Return Result
    Executor-->>Presenter: Emit Finished Signal
    Presenter->>Presenter: _untrack(handle)
    Presenter->>View: Show Result
```

---

## 4. Standard Task Lifecycle

When a User clicks the "Run" button on the UI, the event flow occurs as follows:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant View
    participant Presenter
    participant Executor as QtTaskExecutor
    participant Task as Domain Task (Worker Thread)
    participant Ctx as QtTaskContext (Signals)
    
    User->>View: Click "Start"
    View->>Presenter: on_start_clicked()
    
    Presenter->>Executor: submit(DomainTask)
    Executor->>Ctx: Instantiate Context
    Executor->>Task: Enqueue in QThreadPool
    Executor-->>Presenter: Return TaskHandle
    
    Presenter->>Presenter: _track(handle)
    Presenter->>TaskHandle: subscribe_progress(update_ui)
    
    note over Task, Ctx: Worker Thread Execution
    loop Every processing step
        Task->>Ctx: report_progress()
        Ctx-->>View: Emit Qt Signal (Queued)
        View->>Presenter: Execute Callback (update_ui)
        Presenter->>Presenter: Check if is_alive
        Presenter->>View: view.set_progress()
    end
    
    Task-->>Executor: Return Output Result
    Executor-->>Presenter: Emit Finished Signal
    Presenter->>Presenter: _untrack(handle)
    Presenter->>View: Display Result
```

---

## 5. Anti-Zombie / Self-Cleanup Mechanism

One of the most critical issues in UI applications is when a User closes a window while a background Task is still running. The framework completely resolves this through the following mechanism:

```mermaid
stateDiagram-v2
    [*] --> WindowOpen: User opens View
    WindowOpen --> TaskRunning: User starts Task
    
    state TaskRunning {
        direction LR
        WorkerThread --> UpdateGUI: Emits Signal
    }
    
    TaskRunning --> CloseEvent: User clicks [X]
    
    CloseEvent --> BaseQtView
    BaseQtView --> BasePresenter: calls cleanup()
    
    BasePresenter --> ViewDetached: is_alive = False
    BasePresenter --> HandleCancel: handle.cancel()
    
    ViewDetached --> SignalIgnored: Worker emits signal
    SignalIgnored --> [*]: Safely dropped
    
    HandleCancel --> TaskStops: Task calls ctx.is_cancelled() == True
    TaskStops --> [*]: Thread exit
```

---

## 6. Guidelines for Developers & AI

1.  **Test Location (`framework/tests`)**: Never write Unit Tests for GUI logic. Tests must strictly cover the Core, Executor, Context, and Base Presenter components within the `framework/tests` directory.
2.  **View Inheritance**: Every View MUST inherit from `framework.ui.views.BaseQtView`. Do not inherit from `QWidget` directly.
3.  **Presenter Inheritance**: Every Presenter MUST inherit from `framework.ui.presenters.BasePresenter`. The very first line of the overridden `bind()` method MUST be `super().bind(view)`.
4.  **The `is_alive` Guard**: Any Presenter method executed as a Callback (e.g., `on_progress`, `on_finished`) MUST begin with the safety guard:
    ```python
    if not self.is_alive:
        return
    ```
5.  **Bootstrap Exclusivity**: Always use `FrameworkContext` for initialization. Never manually instantiate `TaskExecutor` or `TaskRepository` outside of the `framework/bootstrap.py` file.

*This document serves as the "Source of Truth" for the entire UI Framework Architecture.*
