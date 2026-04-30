# CodeSkeleton

## 📁 Project Structure

```
framework/
    core/
        task.py
        task_context.py
        task_state.py
        task_executor.py
        task_repository.py
        task_registry.py

    runtime/
        qt_executor.py
        cli_executor.py

    adapters/
        qt/
            qt_context.py
        cli/
            cli_context.py

domain/
    tasks/
        demo_task.py

ui/
    presenters/
        base_presenter.py
        demo_presenter.py
    views/
        demo_view.py

app/
    main_qt.py
    main_cli.py
```

---

# 🧱 framework/core

## task.py

```python
from abc import ABC, abstractmethod
from typing import Any

class Task(ABC):
    @abstractmethod
    def run(self, ctx) -> Any:
        pass
```

---

## task_context.py

```python
class TaskContext:
    def report_progress(self, value: int):
        pass

    def report_message(self, message: str):
        pass

    def log(self, message: str):
        pass

    def is_cancelled(self) -> bool:
        return False
```

---

## task_state.py

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskState:
    id: str
    status: TaskStatus
    progress: int = 0
    result: Any = None
    error: Optional[str] = None
```

---

## task_executor.py

```python
from abc import ABC, abstractmethod

class TaskHandle:
    def cancel(self):
        pass

    def subscribe(self, callback):
        pass

    def get_state(self):
        pass


class TaskExecutor(ABC):
    @abstractmethod
    def submit(self, task):
        pass
```

---

## task_repository.py

```python
class TaskRepository:
    def __init__(self):
        self._tasks = {}

    def add(self, state):
        self._tasks[state.id] = state

    def update(self, state):
        self._tasks[state.id] = state

    def get(self, task_id):
        return self._tasks.get(task_id)
```

---

## task_registry.py

```python
class TaskRegistry:
    def __init__(self):
        self._map = {}

    def register(self, task_type, factory):
        self._map[task_type] = factory

    def create(self, task_type, *args, **kwargs):
        factory = self._map[task_type]
        return factory(*args, **kwargs)
```

---

# ⚙️ framework/adapters

## qt/qt_context.py

```python
from PySide6.QtCore import QObject, Signal
from framework.core.task_context import TaskContext

class QtSignals(QObject):
    progress = Signal(int)
    message = Signal(str)
    finished = Signal(object)

class QtTaskContext(TaskContext):
    def __init__(self):
        super().__init__()
        self.signals = QtSignals()
        self._cancelled = False

    def report_progress(self, value: int):
        self.signals.progress.emit(value)

    def report_message(self, message: str):
        self.signals.message.emit(message)

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True
```

---

## cli/cli_context.py

```python
from framework.core.task_context import TaskContext

class CLITaskContext(TaskContext):
    def __init__(self):
        self._cancelled = False

    def report_progress(self, value: int):
        print(f"[PROGRESS] {value}%")

    def report_message(self, message: str):
        print(f"[INFO] {message}")

    def log(self, message: str):
        print(f"[LOG] {message}")

    def is_cancelled(self):
        return self._cancelled
```

---

# ⚙️ framework/runtime

## qt_executor.py

```python
from PySide6.QtCore import QRunnable, QThreadPool
import uuid

from framework.core.task_executor import TaskExecutor, TaskHandle
from framework.core.task_state import TaskState, TaskStatus
from framework.adapters.qt.qt_context import QtTaskContext


class QtTaskHandle(TaskHandle):
    def __init__(self, state, ctx):
        self.state = state
        self.ctx = ctx
        self._subs = []

    def cancel(self):
        self.ctx.cancel()

    def subscribe(self, callback):
        self._subs.append(callback)
        self.ctx.signals.progress.connect(callback)

    def get_state(self):
        return self.state


class Worker(QRunnable):
    def __init__(self, task, ctx, state):
        super().__init__()
        self.task = task
        self.ctx = ctx
        self.state = state

    def run(self):
        try:
            self.state.status = TaskStatus.RUNNING
            result = self.task.run(self.ctx)
            self.state.result = result
            self.state.status = TaskStatus.COMPLETED
        except Exception as e:
            self.state.error = str(e)
            self.state.status = TaskStatus.FAILED


class QtTaskExecutor(TaskExecutor):
    def __init__(self):
        self.pool = QThreadPool()

    def submit(self, task):
        ctx = QtTaskContext()
        state = TaskState(id=str(uuid.uuid4()), status=TaskStatus.PENDING)
        worker = Worker(task, ctx, state)

        handle = QtTaskHandle(state, ctx)

        self.pool.start(worker)
        return handle
```

---

## cli_executor.py

```python
import uuid
from framework.core.task_executor import TaskExecutor, TaskHandle
from framework.core.task_state import TaskState, TaskStatus
from framework.adapters.cli.cli_context import CLITaskContext


class CLITaskHandle(TaskHandle):
    def __init__(self, state):
        self.state = state

    def cancel(self):
        pass

    def subscribe(self, callback):
        pass

    def get_state(self):
        return self.state


class CLITaskExecutor(TaskExecutor):
    def submit(self, task):
        ctx = CLITaskContext()
        state = TaskState(id=str(uuid.uuid4()), status=TaskStatus.RUNNING)

        try:
            result = task.run(ctx)
            state.result = result
            state.status = TaskStatus.COMPLETED
        except Exception as e:
            state.error = str(e)
            state.status = TaskStatus.FAILED

        return CLITaskHandle(state)
```

---

# 🧠 domain

## demo_task.py

```python
import time
from framework.core.task import Task

class DemoTask(Task):
    def run(self, ctx):
        for i in range(5):
            if ctx.is_cancelled():
                return
            time.sleep(1)
            ctx.report_progress((i + 1) * 20)
        return "Done"
```

---

# 🖥️ UI

## presenters/base_presenter.py

```python
class BasePresenter:
    def __init__(self, executor):
        self.executor = executor

    def bind(self, view):
        pass
```

---

## presenters/demo_presenter.py

```python
from ui.presenters.base_presenter import BasePresenter
from domain.tasks.demo_task import DemoTask

class DemoPresenter(BasePresenter):
    def bind(self, view):
        self.view = view
        view.button.clicked.connect(self.start_task)

    def start_task(self):
        task = DemoTask()
        handle = self.executor.submit(task)

        handle.subscribe(self.on_progress)

    def on_progress(self, value):
        self.view.progress.setValue(value)
```

---

## views/demo_view.py

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QProgressBar

class DemoView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.button = QPushButton("Start Task")
        self.progress = QProgressBar()

        layout.addWidget(self.button)
        layout.addWidget(self.progress)
```

---

# 🚀 app

## main_qt.py

```python
from PySide6.QtWidgets import QApplication

from framework.runtime.qt_executor import QtTaskExecutor
from ui.views.demo_view import DemoView
from ui.presenters.demo_presenter import DemoPresenter

app = QApplication([])

executor = QtTaskExecutor()

view = DemoView()
presenter = DemoPresenter(executor)
presenter.bind(view)

view.show()
app.exec()
```

---

## main_cli.py

```python
from framework.runtime.cli_executor import CLITaskExecutor
from domain.tasks.demo_task import DemoTask

executor = CLITaskExecutor()

task = DemoTask()
handle = executor.submit(task)

print("Result:", handle.get_state().result)
```

---

