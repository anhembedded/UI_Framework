# Task-Oriented UI Framework

## Architecture Thesis Defense Document

**Project:** Task-Oriented UI Framework (PySide6 + CLI)
**Document Type:** Architectural Decision Records & Design Rationale
**Status:** Final

---

## Preface

This document is written in the spirit of an academic thesis defense. It does not merely describe *what* the system does — it rigorously argues *why* each architectural decision was made, presents the alternative solutions that were considered and rejected, and defends the chosen design against the most demanding technical scrutiny. Every decision herein is traceable back to a concrete user need.

---

## Part I — Problem Definition & User Stories

### 1.1 The Context: Why Is Desktop UI Development with Threads So Hard?

Building a responsive desktop application in Python using PySide6 or PyQt5 appears straightforward at first. A developer writes some business logic, adds a few widgets, connects signals to slots, and the app works — until it doesn't.

The moment a long-running operation (a file scan, a network request, a computation) is introduced, three fundamental problems emerge simultaneously:

**Problem 1: UI Thread Freezing (The "Spinning Wheel of Death")**
Qt, like all GUI frameworks, runs on a single event loop (the Main Thread). Any blocking call on this thread — even a `time.sleep(1)` — prevents Qt from processing paint events, mouse clicks, and keyboard input. The window freezes, becomes unresponsive, and on Windows, the OS marks it as "Not Responding." Users see a white screen. This is unacceptable in any production application.

**Problem 2: Architectural Coupling (Spaghetti Code)**
The naive fix is to run the work in a `threading.Thread`. But now a new question arises: how does the background thread update the UI? The temptation is to pass the `QProgressBar` directly into the worker function:

```python
# The naive, catastrophic approach
def do_work(progress_bar: QProgressBar):
    for i in range(100):
        time.sleep(0.1)
        progress_bar.setValue(i)  # CRASH: Not safe from worker thread
```

This approach has two fatal problems: it directly couples business logic to a UI widget (making it untestable and non-reusable), and it violates Qt's fundamental thread-safety rule — QWidget instances must only be accessed from the Main Thread.

**Problem 3: Zombie Tasks and Application Crashes**
Even if a developer correctly uses threads and signals, a third problem lurks. When a user closes a window while a background task is still running, what happens? The `QWidget` is destroyed. The thread, however, is still alive. Seconds later, it emits its progress signal. Qt attempts to invoke the connected slot — which references the now-destroyed widget. The result is a fatal crash: `RuntimeError: Internal C++ object already deleted`.

This class of bug is notoriously difficult to reproduce and debug. It is a race condition between the UI destruction event and the thread's next signal emission.

---

### 1.2 User Stories

The framework's entire design is driven by the following five User Stories (US). Every architectural decision in this document is justified by tracing back to one or more of these stories.

---

**US-01 · The Developer wants clean, testable Domain Logic**

> *"As a Developer, I want to write my application's business logic as pure Python — with no dependency on Qt, PySide6, or any UI library — so that I can run, test, and reuse it in isolation without launching a graphical application."*

**Acceptance Criteria:**

- A `Task` class must be importable and instantiable in a plain Python environment (e.g., a `pytest` session) with no Qt installed.
- All methods of `Task` must be callable from a Unit Test using only standard Python objects.
- The task must be able to report progress and status without knowing whether it runs in a Qt or CLI environment.

**Priority:** Critical (P0)

---

**US-02 · The Developer wants to reuse Domain Logic across environments**

> *"As a Developer, I want to take the exact same Task class I wrote for the Qt GUI and run it from the Command Line Interface (CLI) without modifying a single line of the task's code."*

**Acceptance Criteria:**

- The same `MyTask` class runs successfully when submitted to both `QtTaskExecutor` and `CLITaskExecutor`.
- The CLI output (progress, messages) is printed to stdout.
- The Qt GUI output is rendered in the progress bar and status label.
- Zero changes to `MyTask` are required to switch between environments.

**Priority:** Critical (P0)

---

**US-03 · The End User wants a responsive, non-freezing UI**

> *"As an End User, when I click 'Start' to begin a long operation (e.g., scanning 10,000 files), I want the UI to remain fully interactive — I can still move the window, click 'Cancel', and see live progress updates — while the operation runs in the background."*

**Acceptance Criteria:**

- The UI event loop is never blocked by the task's `run()` method.
- Progress bar and status label update smoothly during task execution.
- The Cancel button remains clickable and responsive at all times.
- The application does not display "Not Responding" in the OS window title.

**Priority:** Critical (P0)

---

**US-04 · The End User wants safe, crash-free window closing**

> *"As an End User, I want to be able to close the application window at any time — even when a background task is running — and have the application shut down gracefully without freezing, crashing, or leaving orphaned processes."*

**Acceptance Criteria:**

- Pressing the `[X]` button on the window triggers immediate, clean shutdown.
- All background threads associated with that window are cancelled within a finite timeout.
- No `RuntimeError: Internal C++ object deleted` or `NoneType` crashes occur.
- No orphaned background threads continue to consume CPU/RAM after the window is closed.
- If multiple tasks are running simultaneously, all are cancelled.

**Priority:** Critical (P0)

---

**US-05 · The Developer wants fast, isolated Unit Testing for UI Logic**

> *"As a Developer (or QA Engineer), I want to write Unit Tests for the Presenter's decision-making logic (e.g., 'when the task finishes, does the presenter correctly update the view?') without needing to launch a QApplication, open any window, or depend on any Qt machinery."*

**Acceptance Criteria:**

- A `Presenter` can be instantiated in a `pytest` test function.
- A `MagicMock` object can be used as the `view` argument.
- A lightweight stub can be used as the `executor` argument.
- Assertions can verify that `view.set_progress()` was called with the correct arguments.
- The test suite runs in under 5 seconds without `QApplication` being created.

**Priority:** High (P1)

---

## Part II — Design Phases & Evolution

### 2.1 Phase 0 — Naive Monolithic Approach (Rejected)

**Description:** All logic lives in a single class. The `QMainWindow` subclass directly runs the work in a method, updating its own widgets.

```python
# Phase 0 — What NOT to do
class MyWindow(QMainWindow):
    def on_start(self):
        for i in range(100):
            time.sleep(0.1)
            self.progress_bar.setValue(i)  # Blocks the UI thread
```

**Failures against User Stories:**

- **US-01 FAIL:** Business logic is inseparable from QMainWindow.
- **US-02 FAIL:** Impossible to run from CLI.
- **US-03 FAIL:** UI freezes completely for the duration of the task.
- **US-04 FAIL:** No concept of cancellation.
- **US-05 FAIL:** Cannot test without creating a full QApplication.

**Verdict:** Rejected. This is the anti-pattern the framework is designed to eliminate.

---

### 2.2 Phase 1 — Threaded but Tightly Coupled (Rejected)

**Description:** Business logic is moved to a `threading.Thread`. The thread is given a reference to the widget to update directly.

```python
class MyWindow(QMainWindow):
    def on_start(self):
        def worker(progress_bar):
            for i in range(100):
                time.sleep(0.1)
                progress_bar.setValue(i)  # Crash: wrong thread!
        threading.Thread(target=worker, args=(self.progress_bar,)).start()
```

**Analysis:**

- **US-03 PARTIAL PASS:** The UI thread is no longer blocked.
- **US-01 FAIL:** Logic still depends on a widget reference.
- **US-02 FAIL:** Thread dispatching is tightly coupled to the Qt widget.
- **US-04 FAIL:** Closing the window crashes when the thread next calls `progress_bar.setValue()`.
- **US-05 FAIL:** Impossible to unit test — thread references real widget.

Additionally, this approach has a critical correctness bug: calling `QWidget.setValue()` from a non-main thread is explicitly documented by Qt as undefined behavior (it may work on some platforms and crash on others).

**Verdict:** Rejected. Introduces thread-safety violations while failing to decouple logic.

---

### 2.3 Phase 2 — Signal-Based but No Lifecycle Management (Rejected)

**Description:** A `QObject` worker is created with signals. The worker is moved to a `QThread`. Signals are connected to slots in the main window.

```python
class Worker(QObject):
    progress = Signal(int)
    def run(self):
        for i in range(100):
            time.sleep(0.1)
            self.progress.emit(i)

class MyWindow(QMainWindow):
    def on_start(self):
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
```

**Analysis:**

- **US-03 PASS:** UI thread is free. Signals are dispatched correctly via Qt's Queued Connections.
- **US-01 FAIL:** Domain logic (`Worker`) is still coupled to `QObject` and requires Qt.
- **US-02 FAIL:** Cannot use `Worker` in a plain CLI context.
- **US-04 FAIL:** Closing the window while the thread runs causes crashes. No systematic cancellation mechanism.
- **US-05 PARTIAL:** Can test with `QApplication`, but slow and cumbersome.

Every application would need to re-implement the thread management boilerplate. The approach does not scale.

**Verdict:** Rejected. Correct signal dispatching, but no reusability and no lifecycle safety.

---

### 2.4 Phase 3 — The Final Architecture (Chosen)

The framework systematically addresses each failure from the previous phases through four interconnected architectural decisions.

---

## Part III — Architectural Decisions & Defense

### Decision 1: The `TaskContext` Dependency Inversion (Resolves US-01, US-02)

**The Core Problem:** A `Task` must be able to report progress to the UI, but it must not know *how* that reporting works (Qt Signals, stdout print, a web socket, etc.). This is a classic Dependency Inversion problem.

#### Alternative 1A — Pass a Callback Function

```python
def my_task(progress_callback):
    for i in range(100):
        progress_callback(i)
```

*Why rejected:* A single callback is insufficient. A task needs to report progress, send messages, log diagnostics, and check a cancellation flag. This becomes `my_task(on_progress, on_message, on_log, is_cancelled)` — a messy, fragile signature. Adding a new reporting channel requires changing all task signatures.

#### Alternative 1B — Use a Global Event Bus

*Why rejected:* When multiple instances of the same task type run concurrently (US parallel task demo), the Event Bus cannot distinguish which event belongs to which task without a task ID. Every subscriber must filter, creating complexity and coupling between unrelated components.

#### Alternative 1C — Define `TaskContext` as an Abstract Base Class ✅ **CHOSEN**

```python
class TaskContext(ABC):
    @abstractmethod
    def report_progress(self, value: int): ...
    @abstractmethod
    def report_message(self, msg: str): ...
    @abstractmethod
    def log(self, msg: str): ...
    @abstractmethod
    def is_cancelled(self) -> bool: ...
    @abstractmethod
    def cancel(self) -> None: ...
```

**Defense:**
This is the Ports & Adapters (Hexagonal Architecture) pattern applied precisely. The `Task` (Core) defines a *port* — the interface it needs to communicate. The Framework provides *adapters* that implement that port for each runtime:

- `QtTaskContext` — emits Qt Signals, routes to GUI thread automatically.
- `CLITaskContext` — prints to stdout and routes `log()` to Python's `logging` module.

A `Task` written once can be submitted to any executor in any environment with zero modification. This fully satisfies **US-01** and **US-02**.

The separation of `log()` from `report_message()` is a deliberate design: `report_message()` is for user-visible status ("Processing file 3 of 100"), while `log()` is for developer diagnostics routed to Python's logging infrastructure. Mixing these would pollute the UI with debug noise.

---

### Decision 2: `QThreadPool` + `QRunnable` + Queued Connections (Resolves US-03)

**The Core Problem:** How to run a `Task` on a background thread and have it communicate results back to the Main Thread safely and efficiently?

#### Alternative 2A — `threading.Thread` per Task

*Why rejected:* Creating a new OS thread for every task submission is expensive (each thread consumes ~1-8MB of stack memory). There is no built-in thread reuse. Managing the thread lifecycle (join, daemon flag, exception propagation) requires significant boilerplate per task. Does not integrate with Qt's signal dispatch mechanism.

#### Alternative 2B — `asyncio` with `qasync`

*Why rejected:* The `async/await` paradigm requires the entire call stack to be async — what is called "async contagion." A domain `Task.run()` that calls `async def` must itself be `async def`, which then propagates upward. CPU-bound tasks (which cannot `await`) still block the event loop entirely. The learning curve and maintenance overhead are high for a team not already invested in async Python.

#### Alternative 2C — `QThread` + `QObject.moveToThread()`

*Why rejected:* This is the Qt-canonical approach but requires every task to inherit from `QObject`, reintroducing a Qt dependency in the domain layer (violating US-01). Managing thread start/stop and object ownership across threads is complex and error-prone.

#### Alternative 2D — `QThreadPool` + `QRunnable` ✅ **CHOSEN**

```python
class QtTaskRunner(QRunnable):
    def run(self):
        try:
            result = self.task.run(self.ctx)
            self.state.set_result(result)
        except Exception as e:
            self.state.set_error(str(e))
        finally:
            self.ctx.signals.finished.emit(self.state.snapshot())
```

**Defense:**
`QThreadPool` is Qt's built-in thread pool. It maintains a pool of reusable threads (defaulting to the number of CPU cores), eliminating thread creation overhead for every submission. `QRunnable` is a lightweight unit of work — it does not inherit from `QObject` and imposes no Qt dependency on the domain code.

The critical insight is how the signal dispatch works: when `QtTaskContext` emits a signal (e.g., `progress_updated.emit(50)`) from a Worker Thread, and that signal is connected to a slot in an object living on the Main Thread, Qt automatically uses a **QueuedConnection**. This means Qt serializes the signal emission as an event in the Main Thread's event queue. The Main Thread picks it up safely on its next event loop iteration. This thread-safety guarantee is provided by Qt's C++ runtime at zero cost to the Python developer.

**Threading Summary:**

| Runtime | Mechanism | Thread Safety Guarantee |
|---|---|---|
| Qt | QThreadPool + QRunnable + QueuedConnection | ✅ Qt event queue serializes all UI updates |
| CLI | Synchronous, same thread | ✅ No concurrency; single-threaded |
| State | `threading.Lock` inside `TaskState` | ✅ All mutations via locked setters |
| Cancellation | `_cancelled: bool` atomic on CPython GIL | ✅ Safe flag check in task loop |

---

### Decision 3: Cooperative Cancellation + the `is_alive` Guard (Resolves US-04)

**The Core Problem:** This is the most critical safety problem in the framework. Two independent events can collide: (a) the user closes the window, destroying the UI, and (b) the background thread emitting a signal that references that destroyed UI.

#### Alternative 3A — Force-Kill the Thread

*Why rejected:* Python has no safe API for forcefully terminating a thread. Approaches using ctypes to inject a `SystemExit` exception into a thread can corrupt shared state, prevent file handles and locks from being released, and cause deadlocks. This is never an acceptable production solution.

#### Alternative 3B — Disconnect Signals on Close

*Why rejected:* This prevents the UI from crashing (no slot is called), but the Worker Thread continues running indefinitely, consuming CPU and memory. The task never knows it should stop. This is a CPU/memory leak, not a solution.

#### Alternative 3C — Cooperative Cancellation + `is_alive` Guard ✅ **CHOSEN**

The solution has two complementary layers:

**Layer 1 — Cancellation Signal (stops the task):**
When the window closes, `BaseQtView.closeEvent()` calls `presenter.cleanup()`. The `cleanup()` method calls `handle.cancel()` on every tracked task handle. This sets `ctx._cancelled = True`. The task, in its main loop, calls `ctx.is_cancelled()`. On the next iteration, it sees `True`, returns immediately, and the worker thread exits cleanly.

```python
# Task cooperates in its own cancellation
def run(self, ctx: TaskContext) -> Any:
    for i, item in enumerate(work_items):
        if ctx.is_cancelled():   # Checks the flag every iteration
            return None          # Exits cleanly, thread terminates
        # ... do actual work ...
        ctx.report_progress(i)
```

**Layer 2 — `is_alive` Guard (prevents crash during race condition):**
There is always a finite window of time between when cancellation is requested and when the thread actually stops. During this interval, the thread may emit one final signal. The `is_alive` guard in every Presenter callback is the last line of defense:

```python
def on_progress(self, value: int) -> None:
    if not self.is_alive:  # self.view is None → silently drop the event
        return
    self.view.set_progress(value)  # Only reached if view still exists
```

`is_alive` is implemented as `return self.view is not None`. After `cleanup()` sets `self.view = None`, any concurrent signal arriving at `on_progress` hits the guard and returns silently. No crash. No leak.

**The Lifecycle Chain:**

```
User clicks [X]
  → BaseQtView.closeEvent()
      → self._presenter.cleanup()
          → for handle in self._handles: handle.cancel()
          → self._handles.clear()
          → self.view = None           ← is_alive becomes False
      → self._presenter = None
  → super().closeEvent(event)           ← Qt destroys the window
```

This chain is **only guaranteed** if all three conditions are met:

1. `View` inherits `BaseQtView` (not raw `QWidget`).
2. `view._set_presenter(self)` is called in `Presenter.bind()`.
3. `super().bind(view)` is the first line of `Presenter.bind()`.

The framework's Base classes enforce this contract through documentation, type hints, and runtime assertions.

---

### Decision 4: `FrameworkContext` as Composition Root (Resolves US-05)

**The Core Problem:** Where are dependencies (executor, repository, factory) created and wired together? The answer determines the testability of the entire codebase.

#### Alternative 4A — Instantiate Dependencies Inside `Presenter.__init__`

```python
class MyPresenter(BasePresenter):
    def __init__(self):
        self.executor = QtTaskExecutor()  # Hardcoded! Cannot swap in tests.
```

*Why rejected:* The Presenter is now welded to `QtTaskExecutor`. A Unit Test cannot substitute a fast, in-memory mock executor. Every test would require a full Qt runtime.

#### Alternative 4B — A Global Singleton Executor

```python
# global.py
EXECUTOR = QtTaskExecutor()
```

*Why rejected:* Global mutable state is the enemy of Unit Testing. Test isolation requires that each test starts with a clean state. A shared global executor carries state between tests, causing non-deterministic failures (flaky tests). It also prevents running tests in parallel.

#### Alternative 4C — Manual Dependency Injection at the Call Site

Each `App.run()` manually creates and passes dependencies. This works, but every app must re-implement the same boilerplate of creating `QApplication`, `TaskRepository`, `QtTaskExecutor`, `PresenterFactory`, binding them together, etc.

#### Alternative 4D — `FrameworkContext` (Composition Root / DI Container) ✅ **CHOSEN**

```python
# The 3-step Composition Root pattern — every App.run() looks exactly like this
ctx = FrameworkContext.qt()            # 1. Bootstrap: create all services once
ctx.register(MyView, MyPresenter)      # 2. Register: declare view-presenter mapping
view, _ = ctx.wire(MyView())           # 3. Wire: inject + bind in one call
view.show()
```

**Defense:**

`FrameworkContext` is a Composition Root — the single, well-known location where all object graphs are assembled. Its benefits are:

1. **Testability (solves US-05):** A `Presenter` can be instantiated with a `MagicMock` as executor in a test, completely bypassing `FrameworkContext`. The `bind()` method accepts any object with the `TaskExecutor` interface.

2. **Consistency:** All applications share the same 3-step bootstrap ritual. A developer onboarding to the project immediately recognizes the pattern regardless of which specific app they are reading.

3. **Extensibility:** Adding a new runtime (e.g., AsyncIO) requires adding one new classmethod `FrameworkContext.asyncio()` that creates an `AsyncTaskExecutor`. All other code remains unchanged.

4. **Decoupled Factory:** `PresenterFactory` is a pure lookup table (view class → presenter class). It does not store the executor. The executor is injected at `create()` time, keeping the factory stateless and reusable.

---

## Part IV — Testing Strategy

### 4.1 Design Principles

The testing strategy follows the **AAA Pattern** (Arrange, Act, Assert) and enforces one behavior per test. Tests assert on **observable behavior** — return values, state, and method call counts — never on private implementation details.

### 4.2 Test Isolation Boundary

The framework draws a deliberate line:

| What is tested | How | Tool |
|---|---|---|
| `Task` domain logic | Run with `CLITaskContext` stub | Pure pytest, no Qt |
| `TaskState` thread safety | Direct mutation + snapshot | Pure pytest |
| `CLITaskExecutor` | Submit real task, read handle state | Pure pytest |
| `BasePresenter` logic | MagicMock as view, stub executor | Pure pytest |
| `FrameworkContext.wire()` | Integration test | Pure pytest |
| `QtTaskExecutor` signals | Requires QApplication | pytest-qt |

The `qt` marker gates slow, Qt-dependent tests. Running `pytest -m "not qt"` executes all pure-Python tests in under 2 seconds — satisfying **US-05** completely.

### 4.3 Mock Policy

| Component | Policy |
|---|---|
| Task stubs | Real `Task` subclasses (preserves contract) |
| View in Presenter tests | `MagicMock` |
| Executor in Presenter tests | `StubExecutor` (real `TaskHandle` return) |
| Qt Signals | Never mocked; use `pytest-qt` QApplication |

---

## Part V — Summary & Conclusion

### 5.1 Traceability Matrix

| User Story | Architectural Decision | Key Component |
|---|---|---|
| US-01 (Clean Domain) | `TaskContext` ABC (Ports & Adapters) | `framework/core/task_context.py` |
| US-02 (Reusability) | `TaskContext` ABC + dual Adapters | `CLITaskContext`, `QtTaskContext` |
| US-03 (Responsive UI) | QThreadPool + QRunnable + Queued Connections | `framework/runtime/qt_executor.py` |
| US-04 (Safe Lifecycle) | Cooperative Cancellation + `is_alive` guard | `BasePresenter`, `BaseQtView` |
| US-05 (Fast Unit Tests) | Composition Root + Injected Dependencies | `FrameworkContext`, `PresenterFactory` |

### 5.2 Architectural Properties Achieved

**Separation of Concerns:** Domain, UI, Runtime, and Wiring each live in isolated layers with clearly defined interfaces between them. No layer imports from a layer above it in the hierarchy.

**Open/Closed Principle:** The framework is open for extension (add new `Task`, new `App`, new Runtime Adapter) and closed for modification (existing base classes and contracts do not need to change).

**Single Responsibility:** Each class has exactly one reason to change. `Task` changes only when business logic changes. `BasePresenter` changes only when the presenter lifecycle protocol changes. `FrameworkContext` changes only when the bootstrap ritual changes.

**Testability:** Every behavioral unit can be tested in isolation. The entire framework's unit test suite runs without PySide6 installed on the test machine (with the exception of Qt-integration tests, which are marked and can be skipped).

### 5.3 The Cost of This Architecture

An honest thesis defense acknowledges trade-offs. This framework imposes a structural overhead on developers:

- Every new feature requires creating separate files for Task, View, and Presenter.
- Developers must consciously follow the `is_alive` guard pattern in every Presenter callback.
- The `register()` → `wire()` ritual must be understood before an app can be bootstrapped.

These are deliberate costs. They are the price of the safety, testability, and scalability guarantees the framework provides. For a single-screen toy application, the overhead may not be worth it. For a multi-tab, multi-task enterprise desktop tool that must not crash and must be maintainable over years by multiple developers, this architecture is not over-engineering — it is a prerequisite.

### 5.4 Final Statement

This framework is not a collection of utilities. It is a formalized, opinionated set of contracts and base classes that embody hard-won lessons from real-world Qt application development. Every rule it enforces — inherit `BaseQtView`, call `super().bind(view)`, guard with `is_alive` — exists because the absence of that rule causes a specific, reproducible class of failures.

The framework answers a simple question: *"How do you build a desktop application in Python that is responsive, testable, safe, and maintainable?"* — and it answers it with a complete, internally consistent architectural solution.

*End of Thesis Defense Document.*
