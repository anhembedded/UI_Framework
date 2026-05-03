"""
framework.adapters — Runtime Adapter Layer
==========================================
Version : 1.0.0
SDD     : Design/SDD/SDD_adapters.md

Concrete implementations of TaskContext for each supported runtime.
Acts as the bridge between pure domain Tasks and the hosting environment.

Sub-packages:
  - adapters.qt   : QtTaskContext + QtTaskSignals (PySide6, cross-thread signals).
  - adapters.cli  : CLITaskContext (stdout print + Python logging).

Rule: The Core (framework.core) must NEVER import from this package.
      Dependency only flows inward (Dependency Inversion Principle).
"""
