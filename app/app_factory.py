"""Application layer: AppFactory + runtime-specific App classes.

Demo apps now live inside the app/ package:
    app/demo_basic/
    app/demo_multi_task/
    app/demo_file_processor/
    app/demo_mdi/

Wiring pattern (every BaseApp.run() follows 3 steps):
    ctx = FrameworkContext.qt()               # 1. Bootstrap services
    ctx.register(MyView, MyPresenter)         # 2. Declare view-presenter pairs
    view, _ = ctx.wire(MyView())              # 3. Wire + show

Usage:
    python main.py                     # demo_basic Qt GUI
    python main.py --cli               # demo_basic CLI
    python main.py --app=multi         # demo_multi_task Qt
    python main.py --app=files         # demo_file_processor Qt
    python main.py --app=mdi           # demo_mdi Qt
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Type



# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseApp(ABC):
    @abstractmethod
    def run(self) -> None:
        pass


# ---------------------------------------------------------------------------
# demo_basic
# ---------------------------------------------------------------------------

class QtDemoBasicApp(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from framework.bootstrap import FrameworkContext
        from app.demo_basic.views.demo_view import DemoView
        from app.demo_basic.presenters.demo_presenter import DemoPresenter

        app = QApplication(sys.argv)
        ctx = FrameworkContext.qt()
        ctx.register(DemoView, DemoPresenter)
        view, _ = ctx.wire(DemoView())
        view.show()
        sys.exit(app.exec())


class CLIDemoBasicApp(BaseApp):
    def run(self) -> None:
        from framework.bootstrap import FrameworkContext
        from app.demo_basic.tasks.demo_task import DemoTask

        ctx = FrameworkContext.cli()
        print("=== Demo Basic — CLI ===\n")
        handle = ctx.executor.submit(DemoTask())
        state = handle.get_state()
        print(f"\nStatus : {state.status.value}")
        print(f"Result : {state.result}")


# ---------------------------------------------------------------------------
# demo_multi_task
# ---------------------------------------------------------------------------

class QtDemoMultiTaskApp(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from framework.bootstrap import FrameworkContext
        from app.demo_multi_task.views.multi_task_view import MultiTaskView
        from app.demo_multi_task.presenters.multi_task_presenter import MultiTaskPresenter

        app = QApplication(sys.argv)
        ctx = FrameworkContext.qt()
        ctx.register(MultiTaskView, MultiTaskPresenter)
        view, _ = ctx.wire(MultiTaskView())
        view.show()
        sys.exit(app.exec())


class CLIDemoMultiTaskApp(BaseApp):
    def run(self) -> None:
        from framework.bootstrap import FrameworkContext
        from app.demo_multi_task.tasks.work_task import WorkTask

        ctx = FrameworkContext.cli()
        print("=== Demo Multi-Task — CLI (3 tasks sequentially) ===\n")
        for i in range(1, 4):
            handle = ctx.executor.submit(WorkTask(name=f"Worker-{i}", steps=4))
            s = handle.get_state()
            print(f"  {s.result or 'cancelled/failed'}")


# ---------------------------------------------------------------------------
# demo_file_processor
# ---------------------------------------------------------------------------

class QtDemoFileProcessorApp(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from framework.bootstrap import FrameworkContext
        from app.demo_file_processor.views.file_processor_view import FileProcessorView
        from app.demo_file_processor.presenters.file_processor_presenter import FileProcessorPresenter

        app = QApplication(sys.argv)
        ctx = FrameworkContext.qt()
        ctx.register(FileProcessorView, FileProcessorPresenter)
        view, _ = ctx.wire(FileProcessorView())
        view.show()
        sys.exit(app.exec())


class CLIDemoFileProcessorApp(BaseApp):
    def run(self) -> None:
        from framework.bootstrap import FrameworkContext
        from framework.core.task_timeout import WithTimeout
        from app.demo_file_processor.tasks.file_scan_task import FileScanTask

        directory = "."
        print(f"=== Demo File Processor — CLI ===\nScanning: {directory}\n")
        ctx = FrameworkContext.cli()
        task = WithTimeout(FileScanTask(directory), timeout_sec=30.0)
        handle = ctx.executor.submit(task)
        state = handle.get_state()
        if state.result:
            results = state.result.get("results", [])
            print(f"Found {len(results)} file(s):")
            for r in results[:20]:
                print(f"  {r['rel_path']:40s}  {r['lines']:5d} lines  {r['words']:6d} words")
        print(f"\nStatus: {state.status.value}")


# ---------------------------------------------------------------------------
# demo_mdi
# ---------------------------------------------------------------------------

class QtDemoMdiApp(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from framework.bootstrap import FrameworkContext
        from app.demo_mdi.views.mdi_main_window import MdiMainWindow
        from app.demo_mdi.presenters.mdi_main_presenter import MdiMainPresenter

        app = QApplication(sys.argv)
        ctx = FrameworkContext.qt()
        window = MdiMainWindow()
        presenter = MdiMainPresenter(ctx.executor)
        presenter.bind(window)
        window.show()
        sys.exit(app.exec())

class QT_New_App(BaseApp):
    def run(self) -> None:
        from PySide6.QtWidgets import QApplication
        from framework.bootstrap import FrameworkContext
        from app.new_demo_app.views.View_MainWindow import View_MainWindow
        from app.new_demo_app.presenters.Presenter_MainWindow import Presenter_MainWindow

        app = QApplication(sys.argv)
        frameworkContext = FrameworkContext.qt()
        
        window = View_MainWindow()
        presenter = Presenter_MainWindow(frameworkContext.executor)
        presenter.bind(window)
        window.show()
        sys.exit(app.exec())

class CLI_New_App(BaseApp):
    def run(self) -> None:
        print("new_demo demo is CLI-only.  Run: python main.py --app=new_demo")


class CLIDemoMdiApp(BaseApp):
    def run(self) -> None:
        print("MDI demo is Qt-only.  Run: python main.py --app=mdi")


# ---------------------------------------------------------------------------
# AppFactory
# ---------------------------------------------------------------------------

class AppFactory:
    """Selects the correct BaseApp from argv flags.

    Flags:
        --app=<name>   App key. Default: basic.
        --cli          CLI mode instead of Qt GUI.

    To add a new app: add ONE tuple to _REGISTRY.
    """

    _REGISTRY: Dict[str, Tuple[Type[BaseApp], Type[BaseApp]]] = {
        "basic": (QtDemoBasicApp,         CLIDemoBasicApp),
        "multi": (QtDemoMultiTaskApp,     CLIDemoMultiTaskApp),
        "files": (QtDemoFileProcessorApp, CLIDemoFileProcessorApp),
        "mdi":   (QtDemoMdiApp,           CLIDemoMdiApp),
        "new_demo":  (QT_New_App, CLI_New_App)
    }

    @classmethod
    def from_args(cls, argv: List[str]) -> BaseApp:
        import logging
        from framework.logging_setup import setup_logging, setup_exception_handler

        setup_logging(level=logging.INFO)
        setup_exception_handler()

        app_name = "basic"
        is_cli = "--cli" in argv

        for arg in argv:
            if arg.startswith("--app="):
                app_name = arg.split("=", 1)[1]

        if app_name not in cls._REGISTRY:
            keys = list(cls._REGISTRY.keys())
            raise SystemExit(
                f"Unknown app '{app_name}'. Available: {keys}\n"
                f"Usage: python main.py [--app={'|'.join(keys)}] [--cli]"
            )

        qt_cls, cli_cls = cls._REGISTRY[app_name]
        chosen = cli_cls() if is_cli else qt_cls()
        logging.getLogger(__name__).info(
            "Starting app='%s' mode='%s'", app_name, "cli" if is_cli else "qt"
        )
        return chosen
