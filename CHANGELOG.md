# CHANGELOG

All notable changes to **Task-Oriented UI Framework** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-04-30  ·  Initial Release

### Added — Framework Core

| Component | Description |
|---|---|
| `Task` ABC | Pure-Python domain logic base class. Zero Qt dependency. |
| `TaskContext` ABC | Full abstract interface: `report_progress`, `report_message`, `log`, `is_cancelled`, `cancel`. ALL methods abstract — missing any raises `TypeError` at instantiation. |
| `TaskState` | Thread-safe dataclass with `threading.Lock`. Locked setters (`set_status`, `set_result`, `set_error`, `set_progress`). `snapshot()` for safe GUI-thread reads. |
| `TaskStatus` | Enum: `PENDING → RUNNING → COMPLETED / FAILED / CANCELLED`. |
| `TaskExecutor` ABC | `submit(task) → TaskHandle`. |
| `TaskHandle` base | `cancel()`, `subscribe()`, `subscribe_message()`, `subscribe_finished()`, `subscribe_error()`, `get_state()`. |
| `TaskRepository` | In-memory CRUD store for `TaskState`. `all()` returns a copy. |
| `TaskRegistry` + `TaskFactory` | Optional registry pattern for dynamic task creation. |
| `WithTimeout` | Decorator-style task wrapper. Fires `ctx.cancel()` after `timeout_sec` via `threading.Timer`. Works with any runtime. |

### Added — Adapters & Runtime

| Component | Description |
|---|---|
| `QtTaskContext` | Routes `report_progress / report_message` to Qt Signals (queued → GUI thread safe). `log()` goes to Python `logging` module, NOT to UI. |
| `CLITaskContext` | `report_progress / report_message` → `print()`. `log()` → Python `logging` (DEBUG level). `cancel()` sets bool flag (cooperative). |
| `QtTaskExecutor` | Submits tasks to `QThreadPool.globalInstance()` via `QRunnable`. Returns `QtTaskHandle` with signal subscriptions. |
| `CLITaskExecutor` | Synchronous, blocks until task completes. `CLITaskHandle.subscribe()` raises `UserWarning` instead of silently doing nothing (P0 fix). |
| `logging_setup.py` | `setup_logging(level, log_file)` — rotating file handler optional. `setup_exception_handler()` — installs `sys.excepthook`. |

### Added — UI Layer

| Component | Description |
|---|---|
| `BaseQtView` | `QWidget` subclass. Overrides `closeEvent` → calls `presenter.cleanup()`. Stores `_presenter` ref; drops it on close. |
| `BasePresenter` | Multi-handle tracking (`_handles: List`). `is_alive` property (P0 null guard). `cleanup()` cancels ALL handles, idempotent. `bind()` connects `view.destroyed` as secondary cleanup trigger. |
| `PresenterFactory` | Pure lookup table. Executor is **NOT** stored — injected at `create(view, executor)` time. |

### Added — Application Layer

| Component | Description |
|---|---|
| `FrameworkContext` | **Single Point of Wiring** / lightweight DI container. Factory methods `FrameworkContext.qt()` and `FrameworkContext.cli()` create all framework services in one call. Fluent `register()` + `wire(view)` API. |
| `AppFactory` | Dispatches to correct `BaseApp` subclass from `--app=<name>` and `--cli` flags. Calls `setup_logging()` + `setup_exception_handler()` on startup. |
| `BaseApp` | Abstract base with `run()`. All concrete apps are 3-line compositions: `FrameworkContext.qt()` → `register()` → `wire()`. |

### Added — Demo Applications

| App | Key | Description |
|---|---|---|
| Demo Basic | `basic` | 5-step synchronous task. Simple progress bar + cancel. |
| Demo Multi-Task | `multi` | Unlimited parallel tasks. Dynamic card widgets per task. Multi-handle presenter. |
| Demo File Processor | `files` | Scans directory for text files, counts words/lines. 30-second `WithTimeout`. Results in `QTableWidget`. |
| Demo MDI | `mdi` | `QMainWindow` + `QMdiArea`. Open/close sub-windows to verify cleanup lifecycle. Live log console via `QtLogHandler` (thread-safe Qt signal bridge). |

### Added — Testing

- **77 unit tests** across 9 modules, all following AAA pattern.
- Markers: `qt` (requires QApplication), `slow` (uses real sleep).
- `run_tests.ps1` — PowerShell runner with options: `-Fast`, `-Coverage`, `-Html`, `-Module`, `-Filter`, `-FailFast`, `-Verbose`.
- `pytest.ini_options` and `[tool.coverage]` configured in `pyproject.toml`.

### Added — Documentation

- `Design/Software Design Document.md` — full architecture SDD
- `Design/Architecture_Tutorial.md` — problem → solution learning guide
- `Design/Class_Diagram.puml` — PlantUML class diagram v2
- `Design/Sequence_Diagram.puml` — 8-phase complete lifecycle diagram
- `Design/Project Structure.md` — directory map
- `Design/AI-Guide.md` — AI developer guide with anti-patterns, best practices, step-by-step examples
- `README.md` — quick-start usage guide

### Fixed (P0 — Critical)

- **NoneType crash on closed window:** All presenter callbacks now guard with `if not self.is_alive: return`. Queued signals arriving after window close are safely ignored.
- **Silent subscribe() no-op in CLI:** `CLITaskHandle.subscribe()` now raises `UserWarning` instead of silently doing nothing, preventing silent logic bugs in CLI mode.

### Fixed (P1 — Important)

- **Zombie tasks on window close:** `BasePresenter` tracks all active `TaskHandle` objects in `_handles: List`. `cleanup()` cancels **all** of them, not just the last one.
- **log() mixed with UI messages:** `CLITaskContext.log()` now routes to Python `logging` module (DEBUG level) instead of `print()`. `QtTaskContext.log()` was already correct.
- **DI scatter across App classes:** Replaced `BaseApp._make_repo()` / `_make_executor()` helpers with `FrameworkContext` (single point of wiring). Each `BaseApp.run()` is now 3 lines.

### Fixed (P2 — Quality)

- **No task timeout:** Added `WithTimeout(task, timeout_sec)` decorator. Used in `demo_file_processor` with 30 s limit.
- **No global exception handler:** `setup_exception_handler()` installs `sys.excepthook` that logs unhandled exceptions to the Python logger.
- **No centralized logging:** `setup_logging()` configures root logger with optional rotating file handler.

---

## Run Commands

```bash
# Install
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]

# Run apps
python main.py                    # demo_basic Qt GUI
python main.py --app=multi        # multi-task Qt
python main.py --app=files        # file processor Qt
python main.py --app=mdi          # MDI lifecycle test Qt
python main.py --cli              # demo_basic CLI

# Tests
.\run_tests.ps1 -Fast             # fast suite (no Qt, no sleep)
.\run_tests.ps1 -Coverage         # with coverage report
.\run_tests.ps1 -Module ui        # only ui module tests
.\run_tests.ps1 -Filter cleanup   # tests matching keyword
```

---

## Known Limitations

- Qt executor tests (`test_qt_executor.py`) not yet implemented — requires QApplication fixture.
- No async/await runtime adapter.
- `TaskRegistry` is optional and not wired into `FrameworkContext` by default.
- MDI `MdiMainPresenter` is wired manually (bypasses `PresenterFactory`) because `QMainWindow` is not a `BaseQtView`.

## Roadmap (v0.2.0)

- DI Container with auto-wiring
- Event Bus for cross-component communication
- Router / Window Manager for multi-screen navigation
- `QtTaskExecutor` unit tests with QApplication fixture
- Task retry policy with exponential backoff
- i18n / Localization support
