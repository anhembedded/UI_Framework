# Architecture Tutorial: Problems & Solutions

This document is designed to help you understand *why* this framework is built the way it is. We explore the common pitfalls in Desktop Application development and explain the architectural solutions implemented in this framework.

---

## 1. The Problem: GUI Freezing
**The Issue:**
In UI development, if you run a heavy computation or a network request (e.g., downloading a file) directly inside a button click event, the entire application freezes. The OS might even label the app as "Not Responding."

**The Solution: Background Executors (`TaskExecutor`)**
Instead of running logic in the main GUI thread, we encapsulate the work inside a `Task` object and hand it over to a `TaskExecutor`. 
- In Qt Mode, the `QtTaskExecutor` places the task inside a `QRunnable` and runs it in a background thread using `QThreadPool`. 
- The GUI remains perfectly smooth and responsive.

---

## 2. The Problem: Cross-Thread Communication Crashes
**The Issue:**
You moved your heavy work to a background thread. Now, you want to update a progress bar on the screen. If you modify a UI element directly from a background thread (e.g., `view.progress_bar.setValue(50)`), the application will crash with a segmentation fault. UI components are NOT thread-safe.

**The Solution: Qt Signals & Queued Connections**
We use `TaskContext` (specifically `QtTaskContext`). When the background thread reports progress, it emits a `Qt Signal`. Qt automatically catches this signal and places it into an event queue. The Main GUI Thread then safely reads the queue and updates the progress bar. We completely avoid mutex locks and thread collisions.

---

## 3. The Problem: Framework Lock-in
**The Issue:**
If your business logic (Domain Layer) imports UI libraries (e.g., `import PySide6`), you can never reuse that code for a Web API, a CLI script, or run automated unit tests without spawning a virtual display. Your logic is tightly coupled to Qt.

**The Solution: Adapter Pattern & Inversion of Control**
Our `Task` classes are "Pure Python." They only interact with a generic interface called `TaskContext`.
- When running in GUI mode, we inject a `QtTaskContext` (which translates messages to Qt Signals).
- When running in CLI mode, we inject a `CLITaskContext` (which translates messages to `print()` statements).
The Domain Logic doesn't know—and doesn't care—where it's running.

---

## 4. The Problem: Zombie Tasks and "C++ Object Deleted" Errors
**The Issue:**
A user clicks "Start Download" and immediately closes the application window. 
1. The background thread keeps downloading the file, wasting CPU and Network resources (Zombie Task).
2. When the download finishes, the thread tries to tell the View to update. However, the View has already been destroyed by the OS. PySide6 throws a fatal error: `RuntimeError: wrapped C/C++ object has been deleted`.

**The Solution: View Lifecycle Management (`BaseQtView` + `cleanup`)**
We introduced strict lifecycle hooks:
1. Every View inherits from `BaseQtView`. When the user closes the window, it overrides `closeEvent()`.
2. The View immediately notifies the Presenter to run `cleanup()`.
3. The Presenter calls `cancel()` on the ongoing task.
4. The Presenter drops references (`self.view = None`), breaking cyclic dependencies so Python's Garbage Collector can safely free memory.

---

## 5. The Problem: Spaghetti Code in `main.py`
**The Issue:**
As the application grows, the `main.py` file becomes massive. It handles CLI argument parsing, instantiates hundreds of database connections, initializes theming, and wires up UI components. It becomes impossible to read or test.

**The Solution: The Composition Root (`AppFactory` & `BaseApp`)**
We keep `main.py` strictly at 3 lines of code. It delegates all responsibility to the `AppFactory`.
The `AppFactory` looks at the terminal arguments and decides which `BaseApp` to boot (`CLIApp` or `QtApp`). 
Each `App` acts as an isolated **Composition Root**—the single place in the codebase where Dependency Injection happens, wiring up Views, Presenters, and Executors in a clean, centralized manner.
