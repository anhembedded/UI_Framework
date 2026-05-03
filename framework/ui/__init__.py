"""
framework.ui — Presentation & View Layer
========================================
Version : 1.0.0
SDD     : Design/SDD/SDD_ui.md

This module provides the base classes for the GUI layer following the MVP pattern.

Key Contracts:
  - BaseQtView      : Base class for all PySide6 Views. Ensures lifecycle hooks
                      (like closeEvent) trigger safe presenter cleanup.
  - BasePresenter   : Core MVP Presenter. Manages task subscription, thread-safe
                      UI updates via `is_alive` guards, and zombie task prevention.
  - PresenterFactory: Centralized registry for View <-> Presenter mappings.
"""
