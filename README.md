# Task-Oriented UI Framework (PySide6 + CLI)

This is a modern, modular, and thread-safe Python framework designed for building desktop applications. It cleanly separates domain logic from the User Interface, allowing the exact same business logic to run seamlessly in both a PySide6 GUI and a Command-Line Interface (CLI).

## Installation

We recommend using a virtual environment. Install the framework in editable mode:

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install the framework and dependencies (PySide6)
pip install -e .
```

## How to Run

Because the framework uses a central `AppFactory`, you can run different interfaces using the same entry point:

```bash
# Run the Qt GUI (Default)
python main.py

# Run the Headless CLI Mode
python main.py --cli
```

## How to Use the Framework

### 1. Create a Domain Task
Tasks hold your core business logic. They must NOT import anything from PySide6. They report progress and check for cancellation via the `TaskContext`.

```python
import time
from framework.core.task import Task

class MyDownloadTask(Task):
    def run(self, ctx):
        for i in range(10):
            if ctx.is_cancelled():
                return "Cancelled by user"
            
            time.sleep(1) # Simulate work
            ctx.report_progress((i + 1) * 10)
            ctx.report_message(f"Downloading chunk {i+1}...")
        
        return "Download Complete!"
```

### 2. Create the View (UI)
Views handle the visual layout. Inherit from `BaseQtView` so the framework automatically cleans up resources when the window is closed.

```python
from PySide6.QtWidgets import QPushButton, QVBoxLayout
from ui.views.base_qt_view import BaseQtView

class MyView(BaseQtView):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.btn_start = QPushButton("Start Download")
        layout.addWidget(self.btn_start)
```

### 3. Create the Presenter
Presenters act as the middleman. They listen to the View's events, submit Tasks to the Executor, and update the View with the results.

```python
from ui.presenters.base_presenter import BasePresenter
from framework.core.task_state import TaskStatus

class MyPresenter(BasePresenter):
    def bind(self, view):
        super().bind(view) # Crucial: enables lifecycle hooks
        view.btn_start.clicked.connect(self.start_download)

    def start_download(self):
        task = MyDownloadTask()
        handle = self.executor.submit(task)
        handle.subscribe_finished(self.on_finished)

    def on_finished(self, status: TaskStatus):
        print(f"Task finished with status: {status.name}")
```

### 4. Register in the Application (Composition Root)
Finally, link your View and Presenter in `app/qt_app.py` inside the `PresenterFactory`.

```python
view_factory.register(MyView, MyPresenter)

view = MyView()
presenter = view_factory.create(view, executor)
presenter.bind(view)
view.show()
```
