"""
framework.core — Pure Domain Layer
===================================
Version : 1.0.0
SDD     : Design/SDD/SDD_core.md

This package is the heart of the framework.
100% Pure Python — zero dependency on Qt, PySide6, or any UI library.

Key contracts defined here:
  - Task          : Abstract base for all domain logic units.
  - TaskContext   : Port for task-to-runtime communication (progress, cancel).
  - TaskExecutor  : Abstract submission interface (submit → TaskHandle).
  - TaskHandle    : Control token returned to the presenter after submit().
  - TaskState     : Thread-safe state snapshot (PENDING → RUNNING → DONE).
  - TaskRepository: In-memory store, single source of truth for all TaskStates.
  - TaskRegistry  : Lookup-based task factory (type key → Task instance).
  - WithTimeout   : Decorator Task that enforces a maximum execution duration.
"""
