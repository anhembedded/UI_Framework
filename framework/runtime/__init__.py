"""
framework.runtime — Execution Engine Layer
==========================================
Version : 1.0.0
SDD     : Design/SDD/SDD_runtime.md

This module implements the execution logic for domain tasks. It takes a
pure Python `Task`, pairs it with the appropriate adapter context, and runs it
in the target environment.

Sub-packages/Modules:
  - qt_executor  : Executes tasks in background threads via QThreadPool.
                   Contains QtTaskRunner (the worker) and QtTaskExecutor.
  - cli_executor : Executes tasks synchronously on the main thread for
                   headless operations and fast unit testing.
"""
