framework/
    bootstrap.py             ← FrameworkContext (Single Point of Wiring / DI Container)
    core/
        task.py              ← Task ABC
        task_context.py      ← TaskContext ABC (report_progress, report_message, log, is_cancelled, cancel)
        task_state.py        ← TaskState + threading.Lock (thread-safe setters + snapshot)
        task_executor.py     ← TaskExecutor ABC + TaskHandle base
        task_repository.py   ← In-memory state store
        task_registry.py     ← TaskRegistry + TaskFactory ABC
        task_timeout.py      ← WithTimeout decorator task

    runtime/
        qt_executor.py       ← QtTaskExecutor (QThreadPool + QRunnable)
        cli_executor.py      ← CLITaskExecutor (synchronous)

    adapters/
        qt/qt_context.py     ← QtTaskContext → Qt Signals (queued, GUI-thread safe)
        cli/cli_context.py   ← CLITaskContext → stdout + Python logging (log() ≠ print)

    logging_setup.py         ← setup_logging() + setup_exception_handler()

        ui/
        views/
            base_qt_view.py      ← BaseQtView (closeEvent lifecycle → cleanup)
        presenters/
            base_presenter.py    ← BasePresenter (is_alive, _handles list, cleanup, _track/_untrack)
            presenter_factory.py ← PresenterFactory (executor injected at create(), not stored)

app/
    __init__.py
    app_factory.py           ← AppFactory + BaseApp + QtApp/CLIApp per demo

apps/
    demo_basic/              ← Simple 5-step progress task
        tasks/demo_task.py
        views/demo_view.py
        presenters/demo_presenter.py

    demo_multi_task/         ← Multiple parallel tasks, dynamic card UI
        tasks/work_task.py
        views/multi_task_view.py
        presenters/multi_task_presenter.py

    demo_file_processor/     ← File scanner, word count, 30 s timeout
        tasks/file_scan_task.py
        views/file_processor_view.py
        presenters/file_processor_presenter.py

    demo_mdi/                ← MDI lifecycle test (open/close sub-windows)
        tasks/long_task.py
        views/task_sub_view.py
        views/mdi_main_window.py
        presenters/task_sub_presenter.py
        presenters/mdi_main_presenter.py

    tests/
        conftest.py              ← Shared fixtures + task stubs
        framework/
            core/
                test_task_state.py      ← 11 tests: defaults, setters, snapshot, thread-safety
                test_task_context.py    ← 4 tests: ABC enforcement, cancel() regression
                test_task_repository.py ← 9 tests: CRUD, isolation
                test_task_timeout.py    ← 3 tests: fast/slow/no-premature-cancel
            runtime/
                test_cli_executor.py    ← 12 tests: COMPLETED/FAILED/CANCELLED, subscribe()
            adapters/
                test_cli_context.py     ← 7 tests: progress, message, log→logging, cancel
        ui/
        test_base_presenter.py      ← 13 tests: is_alive, bind, tracking, idempotent cleanup
        test_presenter_factory.py   ← 6 tests: register, inject, overwrite, KeyError
        bootstrap/
        test_framework_context.py   ← 9 tests: CLI bootstrap, register chain, wire()

main.py                      ← 3-line entry point
pyproject.toml               ← project config + pytest config + coverage config
.gitignore
run_tests.ps1                ← PowerShell runner (-Fast / -Coverage / -Module / -Filter)