# AI Developer Guide — Task-Oriented UI Framework

> **For AI agents:** This guide contains everything you need to implement new features, apps,
> and extensions for this framework correctly on the first attempt.
> Read this **before** writing any code.

---

## Table of Contents

1. [Framework Mental Model](#1-framework-mental-model)
2. [Directory Map — What Lives Where](#2-directory-map--what-lives-where)
3. [Core Contracts (Interfaces)](#3-core-contracts-interfaces)
4. [How to Add a New App — Step-by-Step](#4-how-to-add-a-new-app--step-by-step)
5. [Complete Working Example](#5-complete-working-example)
6. [Anti-Patterns — What NOT to Do](#6-anti-patterns--what-not-to-do)
7. [Best Practices Checklist](#7-best-practices-checklist)
8. [Threading & Safety Rules](#8-threading--safety-rules)
9. [Lifecycle Rules (Critical)](#9-lifecycle-rules-critical)
10. [Extending the Framework](#10-extending-the-framework)

---

## 1. Framework Mental Model

The framework is built around one core idea:

> **A Task is pure Python. The runtime (Qt or CLI) is an interchangeable adapter.**

```
User Action
    → Presenter (UI coordinator)
        → TaskExecutor.submit(task)       # hands task to runtime
            → Worker Thread: task.run(ctx)
                → ctx.report_progress()   # signals back to GUI thread
                → ctx.is_cancelled()      # cooperative cancellation
            → on_finished callback
        → View.set_xxx()                  # update UI
```

**The 3 immutable rules of this architecture:**

| Rule | What it means |
|---|---|
| **Domain is pure Python** | `Task` and `TaskContext` must NEVER import `PySide6` or any UI library |
| **View knows nothing about tasks** | Views only have `set_xxx()` methods and emit button signals |
| **Presenter guards with `is_alive`** | Every callback that touches `self.view` must check `if not self.is_alive: return` first |

---

## 2. Directory Map — What Lives Where

```
UI_FrameworkDev/
│
├── framework/          ← DO NOT MODIFY unless fixing a framework bug
│   ├── core/           ← Pure Python, zero Qt dependency
│   │   ├── task.py              Task ABC
│   │   ├── task_context.py      TaskContext ABC (ALL methods are abstract)
│   │   ├── task_state.py        TaskState with threading.Lock
│   │   ├── task_executor.py     TaskExecutor ABC + TaskHandle base
│   │   ├── task_repository.py   In-memory state store
│   │   ├── task_registry.py     TaskRegistry + TaskFactory ABC
│   │   └── task_timeout.py      WithTimeout wrapper
│   ├── runtime/
│   │   ├── qt_executor.py       QtTaskExecutor (QThreadPool)
│   │   └── cli_executor.py      CLITaskExecutor (synchronous)
│   ├── adapters/
│   │   ├── qt/qt_context.py     Routes calls to Qt Signals
│   │   └── cli/cli_context.py   Routes calls to stdout
│   └── logging_setup.py         setup_logging() + setup_exception_handler()
│
├── ramework/ui/                 ← Framework base classes for UI layer, DO NOT put app code here
│   ├── views/
│   │   └── base_qt_view.py      BaseQtView (QWidget with closeEvent lifecycle)
│   └── presenters/
│       ├── base_presenter.py    BasePresenter (is_alive, _handles, cleanup)
│       └── presenter_factory.py PresenterFactory
│
├── app/                ← Composition root (wiring) — edit when adding a new app
│   └── app_factory.py           AppFactory + all App classes
│
├── app/               ← YOUR APP CODE GOES HERE
│   ├── demo_basic/
│   ├── demo_multi_task/
│   ├── demo_file_processor/
│   └── demo_mdi/
│
└── main.py             ← DO NOT MODIFY (3 lines, calls AppFactory)
```

**Rule:** Every new application goes in `app/<your_app_name>/` with sub-directories:
`tasks/`, `views/`, `presenters/`.

---

## 3. Core Contracts (Interfaces)

### 3.1 `Task` (what you implement for domain logic)

```python
from abc import ABC, abstractmethod
from framework.core.task import Task

class MyTask(Task):
    def __init__(self, param: str) -> None:
        self.param = param

    def run(self, ctx) -> any:          # ctx is a TaskContext
        for i in range(10):
            if ctx.is_cancelled():      # ALWAYS check this in long loops
                return None
            # do work...
            ctx.report_progress(i * 10)        # 0–100
            ctx.report_message(f"Step {i}")    # human-readable string
            ctx.log(f"Debug: processing {i}")  # goes to Python logging, NOT UI
        return "result_value"           # returned via handle.get_state().result
```

**Key rules for Task:**

- NEVER import PySide6, tkinter, or any UI library
- NEVER call `time.sleep()` without checking `ctx.is_cancelled()` nearby
- Return a value (or `None`) — never raise to communicate "done"
- Exceptions ARE caught by the executor → `state.status = FAILED`

### 3.2 `TaskContext` (how the Task communicates back)

| Method | Purpose | Goes to |
| --- | --- | --- |
| `report_progress(int 0-100)` | Progress percentage | Qt: progress signal → progress bar |
| `report_message(str)` | Status text for user | Qt: message signal → label |
| `log(str)` | Developer diagnostic | Python `logging` module (NOT shown in UI by default) |
| `is_cancelled() → bool` | Check if cancelled | Returns flag set by `ctx.cancel()` |
| `cancel()` | Request cancellation | Called by `WithTimeout` or `TaskHandle.cancel()` |

### 3.3 `BasePresenter` (what you subclass for presenters)

```python
from ui.presenters.base_presenter import BasePresenter

class MyPresenter(BasePresenter):
    def bind(self, view) -> None:
        super().bind(view)                    # MANDATORY — enables lifecycle hooks
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)         # MANDATORY — enables closeEvent cleanup
        view.my_button.clicked.connect(self.on_action)

    def on_action(self) -> None:
        task = MyTask(param="value")
        handle = self.executor.submit(task)
        self._track(handle)                   # MANDATORY — enables cleanup() to cancel it

        handle.subscribe(self.on_progress)
        handle.subscribe_message(self.on_message)
        handle.subscribe_finished(lambda s, h=handle: self.on_finished(s, h))
        handle.subscribe_error(self.on_error)

        if self.is_alive:
            self.view.set_running()

    # EVERY callback that touches self.view MUST guard with is_alive
    def on_progress(self, value: int) -> None:
        if not self.is_alive: return          # P0: non-negotiable guard
        self.view.set_progress(value)

    def on_message(self, message: str) -> None:
        if not self.is_alive: return
        self.view.set_message(message)

    def on_finished(self, status, handle=None) -> None:
        if handle:
            self._untrack(handle)             # remove from tracking list
        if not self.is_alive: return
        self.view.set_finished(status)

    def on_error(self, error_msg: str) -> None:
        if not self.is_alive: return
        self.view.set_message(f"Error: {error_msg}")
```

### 3.4 `BaseQtView` (what views must inherit)

```python
from ui.views.base_qt_view import BaseQtView
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QProgressBar

class MyView(BaseQtView):                    # NOT QWidget directly
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.my_button = QPushButton("Start")
        self.progress = QProgressBar()
        layout.addWidget(self.my_button)
        layout.addWidget(self.progress)

    # Only state-setting methods here — no business logic
    def set_running(self):
        self.my_button.setEnabled(False)
        self.progress.setValue(0)

    def set_progress(self, value: int):
        self.progress.setValue(value)

    def set_finished(self, status):
        self.my_button.setEnabled(True)
```

---

## 4. How to Add a New App — Step-by-Step

### Step 1: Create directory structure

```
app/
└── my_app/
    ├── __init__.py         (empty)
    ├── tasks/
    │   ├── __init__.py     (empty)
    │   └── my_task.py
    ├── views/
    │   ├── __init__.py     (empty)
    │   └── my_view.py
    └── presenters/
        ├── __init__.py     (empty)
        └── my_presenter.py
```

### Step 2: Implement `MyTask` (no Qt, no UI)

```python
# app/my_app/tasks/my_task.py
import time
from framework.core.task import Task

class MyTask(Task):
    def run(self, ctx):
        for i in range(10):
            if ctx.is_cancelled():
                return None
            time.sleep(0.5)
            ctx.report_progress((i + 1) * 10)
            ctx.report_message(f"Step {i + 1}/10")
        return "Complete"
```

### Step 3: Implement `MyView` (UI only, no task logic)

```python
# app/my_app/views/my_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel
from PySide6.QtCore import Qt
from framework.core.task_state import TaskStatus
from ui.views.base_qt_view import BaseQtView

class MyView(BaseQtView):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("My App")
        layout = QVBoxLayout(self)
        self.label = QLabel("Ready")
        self.label.setAlignment(Qt.AlignCenter)
        self.start_btn = QPushButton("Start")
        self.cancel_btn = QPushButton("Cancel")
        self.progress = QProgressBar()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.cancel_btn)
        self.cancel_btn.setEnabled(False)

    def set_running(self):
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

    def set_progress(self, value: int):
        self.progress.setValue(value)

    def set_message(self, text: str):
        self.label.setText(text)

    def set_finished(self, status: TaskStatus):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.label.setText("Done!" if status.name == "COMPLETED" else str(status.name))
```

### Step 4: Implement `MyPresenter`

```python
# app/my_app/presenters/my_presenter.py
from ui.presenters.base_presenter import BasePresenter
from apps.my_app.tasks.my_task import MyTask
from framework.core.task_state import TaskStatus

class MyPresenter(BasePresenter):
    def bind(self, view) -> None:
        super().bind(view)
        if hasattr(view, "_set_presenter"):
            view._set_presenter(self)
        view.start_btn.clicked.connect(self.on_start)
        view.cancel_btn.clicked.connect(self.on_cancel)

    def on_start(self) -> None:
        handle = self.executor.submit(MyTask())
        self._track(handle)
        handle.subscribe(self.on_progress)
        handle.subscribe_message(self.on_message)
        handle.subscribe_finished(lambda s, h=handle: self.on_finished(s, h))
        if self.is_alive:
            self.view.set_running()

    def on_cancel(self) -> None:
        for h in list(self._handles):
            h.cancel()

    def on_progress(self, value: int) -> None:
        if not self.is_alive: return
        self.view.set_progress(value)

    def on_message(self, message: str) -> None:
        if not self.is_alive: return
        self.view.set_message(message)

    def on_finished(self, status: TaskStatus, handle=None) -> None:
        if handle: self._untrack(handle)
        if not self.is_alive: return
        self.view.set_finished(status)
```

### Step 5: Register in `app/app_factory.py`

Open `app/app_factory.py` and add:

```python
# Add the import block as a new section
class QtMyApp(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from ui.presenters.presenter_factory import PresenterFactory
        from apps.my_app.views.my_view import MyView
        from apps.my_app.presenters.my_presenter import MyPresenter

        app = QApplication(sys.argv)
        repo = self._make_repo()
        executor = self._make_executor(repo)

        factory = PresenterFactory()
        factory.register(MyView, MyPresenter)

        view = MyView()
        presenter = factory.create(view, executor)
        presenter.bind(view)
        view.show()
        sys.exit(app.exec())


class CLIMyApp(BaseApp):
    def run(self) -> None:
        from framework.runtime.cli_executor import CLITaskExecutor
        from apps.my_app.tasks.my_task import MyTask
        executor = CLITaskExecutor()
        handle = executor.submit(MyTask())
        print(f"Result: {handle.get_state().result}")
```

Then register in `_REGISTRY`:

```python
_REGISTRY = {
    # ... existing entries ...
    "myapp": (QtMyApp, CLIMyApp),    # ← add this line
}
```

### Step 6: Run it

```bash
python main.py --app=myapp          # Qt GUI
python main.py --app=myapp --cli    # CLI
```

---

## 5. Complete Working Example

Below is a **hash-file task** — a real-world example that reads files and computes SHA-256 checksums:

```python
# app/hasher/tasks/hash_task.py
import hashlib
import pathlib
from framework.core.task import Task

class HashFilesTask(Task):
    def __init__(self, directory: str) -> None:
        self.directory = directory

    def run(self, ctx) -> dict:
        files = list(pathlib.Path(self.directory).rglob("*.py"))
        results = {}
        for i, fp in enumerate(files):
            if ctx.is_cancelled():
                ctx.report_message("Hashing cancelled.")
                return results
            data = fp.read_bytes()
            results[str(fp)] = hashlib.sha256(data).hexdigest()
            ctx.report_progress(int((i + 1) / max(len(files), 1) * 100))
            ctx.report_message(f"Hashing {fp.name}")
            ctx.log(f"Hashed {fp} → {results[str(fp)][:12]}…")
        return results
```

To add timeout (P2 feature):

```python
# In the presenter's on_start():
from framework.core.task_timeout import WithTimeout

task = WithTimeout(HashFilesTask(directory), timeout_sec=15.0)
handle = self.executor.submit(task)
```

---

## 6. Anti-Patterns — What NOT to Do

### ❌ NEVER touch the view from a Task

```python
# WRONG — will crash (wrong thread + breaks isolation)
class BadTask(Task):
    def __init__(self, view):
        self.view = view

    def run(self, ctx):
        self.view.progress.setValue(50)   # ← CRASH: cross-thread QWidget access
```

```python
# CORRECT — use ctx
class GoodTask(Task):
    def run(self, ctx):
        ctx.report_progress(50)           # framework handles thread dispatch
```

### ❌ NEVER skip `super().bind(view)` in a Presenter

```python
# WRONG — cleanup lifecycle is broken, memory will leak
class BadPresenter(BasePresenter):
    def bind(self, view):
        # forgot super().bind(view)
        view.btn.clicked.connect(self.on_start)
```

```python
# CORRECT
class GoodPresenter(BasePresenter):
    def bind(self, view):
        super().bind(view)                # MANDATORY first line
        view._set_presenter(self)         # MANDATORY second line
        view.btn.clicked.connect(self.on_start)
```

### ❌ NEVER call view methods without `is_alive` guard

```python
# WRONG — crashes if signal arrives after window is closed
def on_progress(self, value: int) -> None:
    self.view.set_progress(value)         # NoneType crash possible
```

```python
# CORRECT
def on_progress(self, value: int) -> None:
    if not self.is_alive: return          # always first
    self.view.set_progress(value)
```

### ❌ NEVER forget `_track(handle)` after submit

```python
# WRONG — task cannot be cancelled when window closes
def on_start(self):
    handle = self.executor.submit(MyTask())
    handle.subscribe(self.on_progress)    # forgot _track!
```

```python
# CORRECT
def on_start(self):
    handle = self.executor.submit(MyTask())
    self._track(handle)                   # MANDATORY — cleanup() can reach it
    handle.subscribe(self.on_progress)
```

### ❌ NEVER inherit directly from `QWidget` for app views

```python
# WRONG — no closeEvent lifecycle, no cleanup on window close
class BadView(QWidget):
    ...
```

```python
# CORRECT
class GoodView(BaseQtView):              # always inherit BaseQtView
    ...
```

### ❌ NEVER call `subscribe()` on a `CLITaskHandle`

```python
# WRONG — raises UserWarning and does nothing
executor = CLITaskExecutor()
handle = executor.submit(task)
handle.subscribe(my_callback)            # UserWarning, callback never fires
```

```python
# CORRECT for CLI — read state after submit() returns
handle = executor.submit(task)           # blocks until done
state = handle.get_state()               # then read the result
```

### ❌ NEVER store executor or presenter in the factory

```python
# WRONG — PresenterFactory is a LOOKUP TABLE, not a service container
factory = PresenterFactory(executor)     # old API, removed for good reason
```

```python
# CORRECT — executor is injected at create() time
factory = PresenterFactory()
factory.register(MyView, MyPresenter)
presenter = factory.create(view, executor)  # executor injected here
```

---

## 7. Best Practices Checklist

When implementing a new app, verify all of these:

**Task:**

- [ ] Does NOT import PySide6 or any UI library
- [ ] Calls `ctx.is_cancelled()` at least once per loop iteration
- [ ] Returns a value (not raises) on normal completion
- [ ] Uses `ctx.log()` for debug output (not `print()`)
- [ ] Uses `ctx.report_message()` for user-facing status updates

**View:**

- [ ] Inherits from `BaseQtView` (not `QWidget` directly)
- [ ] Has ONLY `set_xxx()` methods — no business logic
- [ ] Widget names match what the presenter expects (e.g. `self.start_btn`)

**Presenter:**

- [ ] First line of `bind()` is `super().bind(view)`
- [ ] Second line calls `view._set_presenter(self)` if view supports it
- [ ] Every `handle` returned from `submit()` is immediately `_track()`-ed
- [ ] Every callback that touches `self.view` starts with `if not self.is_alive: return`
- [ ] `on_finished` calls `self._untrack(handle)` before the `is_alive` check
- [ ] Cancelled tasks → `_untrack` them properly

**AppFactory entry:**

- [ ] Imports are inside `run()` (lazy imports prevent loading Qt in CLI mode)
- [ ] Calls `self._make_repo()` and `self._make_executor(repo)` for consistency
- [ ] Registered in `_REGISTRY` dict

---

## 8. Threading & Safety Rules

| Scenario | Rule |
|---|---|
| Reading `TaskState` from GUI thread | Use `handle.get_state()` which returns `state.snapshot()` (lock-protected copy) |
| Mutating `TaskState` from worker thread | Use locked setters: `state.set_status()`, `state.set_result()`, `state.set_error()` — NEVER set attributes directly |
| Updating UI from worker thread | NEVER do this directly. Use `ctx.report_progress()` → Qt signal → GUI thread |
| Cancellation flag | `_cancelled` bool is read/written atomically on CPython (GIL), safe without extra locking |
| Logging from worker thread | Use `ctx.log()` (routes to Python `logging` which is thread-safe) |

---

## 9. Lifecycle Rules (Critical)

The framework provides automatic cleanup, but ONLY if you follow these rules:

### When a view is closed by the user

```
User closes window
    → BaseQtView.closeEvent()
        → self._presenter.cleanup()
            → all handles in self._handles → handle.cancel()
            → self._handles.clear()
            → self.view = None
        → self._presenter = None
```

This chain **only works** if:

1. View inherits `BaseQtView` (not raw `QWidget`)
2. `view._set_presenter(self)` was called in `bind()`
3. `super().bind(view)` was called (connects `view.destroyed` as backup)

### When using MDI (QMdiSubWindow)

```python
sub = QMdiSubWindow()
sub.setAttribute(Qt.WA_DeleteOnClose)   # MANDATORY — without this, sub-window hides, never deletes
sub.setWidget(my_view)                  # my_view must be BaseQtView
```

With `WA_DeleteOnClose`:

- Close sub-window → `QMdiSubWindow` deleted → its child (`my_view`) deleted
- → `my_view.destroyed` signal fires → `presenter._on_view_destroyed()` → `cleanup()`

### Double cleanup is safe

`BasePresenter.cleanup()` is idempotent:

- Second call on an already-cleaned presenter: `_handles` is empty, `self.view` is already `None`
- No crash, no leak

---

## 10. Extending the Framework

### Adding a new runtime (e.g., AsyncIO)

1. Create `framework/adapters/async_/async_context.py` implementing `TaskContext` ABC
2. Create `framework/runtime/async_executor.py` implementing `TaskExecutor` ABC
3. Add a corresponding `BaseApp` subclass in `app_factory.py`

### Adding Task timeout to an existing task

```python
# In presenter, wrap task before submit:
from framework.core.task_timeout import WithTimeout

def on_start(self) -> None:
    raw_task = MyTask()
    task = WithTimeout(raw_task, timeout_sec=30.0)  # auto-cancels after 30s
    handle = self.executor.submit(task)
    self._track(handle)
    # ... rest of subscriptions
```

### Adding centralized logging at startup

```python
# In app/app_factory.py AppFactory.from_args() (already done):
from framework.logging_setup import setup_logging, setup_exception_handler
setup_logging(level=logging.DEBUG, log_file="app.log")
setup_exception_handler()
```

### Adding global exception handler for Qt thread exceptions

Qt exceptions in the main event loop are NOT caught by `sys.excepthook`. To catch them:

```python
# In your QtApp.run(), before app.exec():
import sys

def qt_exception_hook(exc_type, exc_value, exc_tb):
    import logging
    logging.critical("Qt thread exception", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = qt_exception_hook
```

---

## Quick Reference Card

```
IMPLEMENT NEW APP:
  1. app/my_app/{tasks,views,presenters}/__init__.py  (empty)
  2. app/my_app/tasks/my_task.py    → class MyTask(Task)
  3. app/my_app/views/my_view.py    → class MyView(BaseQtView)
  4. app/my_app/presenters/my_presenter.py → class MyPresenter(BasePresenter)
  5. app/app_factory.py              → add QtMyApp, CLIMyApp, register "myapp"

MANDATORY PATTERNS:
  Task:       if ctx.is_cancelled(): return
  Presenter:  super().bind(view)          ← first line of bind()
              view._set_presenter(self)   ← second line of bind()
              self._track(handle)         ← after every executor.submit()
              if not self.is_alive: return ← first line of every callback
              self._untrack(handle)       ← in on_finished before is_alive check
  View:       class MyView(BaseQtView)   ← always BaseQtView

RUN:
  python main.py --app=<name>
  python main.py --app=<name> --cli
  Available: basic | multi | files | mdi | (your new app key)
```
