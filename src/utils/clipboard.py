"""Обратная совместимость: перенос на `src.ui.clipboard_bindings`."""

from __future__ import annotations

from src.ui.clipboard_bindings import enable_clipboard_bindings as enable_clipboard

__all__ = ["enable_clipboard"]
