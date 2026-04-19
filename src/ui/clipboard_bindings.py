"""
Горячие клавиши буфера обмена для CTkEntry / CTkTextbox и внутренних tk-виджетов.

Ctrl/Cmd+A, C, V, X и Shift+Insert; учёт русской раскладки (keycode, control-char, keysym).
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable

logger = logging.getLogger(__name__)

_CTRL_MASK = 0x0004
_CMD_MASK_DARWIN = (0x0008, 0x0010, 0x100000, 0x200000)


def _has_ctrl(event: Any) -> bool:
    """Нажат Ctrl (Windows/Linux)."""
    return bool(int(getattr(event, "state", 0) or 0) & _CTRL_MASK)


def _has_cmd_darwin(event: Any) -> bool:
    """Нажат Command (macOS)."""
    if sys.platform != "darwin":
        return False
    st = int(getattr(event, "state", 0) or 0)
    return any(st & m for m in _CMD_MASK_DARWIN)


def _resolve_inner(widget: Any) -> Any:
    """Возвращает tk.Entry / tk.Text под CTk-обёрткой."""
    if hasattr(widget, "_entry"):
        return widget._entry
    if hasattr(widget, "_textbox"):
        return widget._textbox
    return widget


def _is_text_like(w: Any) -> bool:
    """True, если виджет ведёт себя как tk.Text."""
    return hasattr(w, "tag_add") and hasattr(w, "index")


def _select_all(w: Any) -> str:
    """Выделяет всё содержимое."""
    try:
        if _is_text_like(w):
            w.tag_remove("sel", "1.0", "end")
            w.tag_add("sel", "1.0", "end")
        else:
            w.selection_range(0, "end")
            w.icursor("end")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Выделить всё: %s", exc)
    return "break"


def _paste(w: Any) -> str:
    """Вставка из буфера в позицию курсора."""
    try:
        text = w.clipboard_get()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Буфер обмена (вставка): %s", exc)
        return "break"
    try:
        w.insert("insert", text)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Вставка: %s", exc)
    return "break"


def _copy(w: Any) -> str:
    """Копирование выделения."""
    try:
        if w.selection_present():
            w.clipboard_clear()
            w.clipboard_append(w.selection_get())
    except Exception as exc:  # noqa: BLE001
        logger.debug("Копирование: %s", exc)
    return "break"


def _cut(w: Any) -> str:
    """Вырезание выделения."""
    try:
        if w.selection_present():
            w.clipboard_clear()
            w.clipboard_append(w.selection_get())
            w.delete("sel.first", "sel.last")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Вырезание: %s", exc)
    return "break"


def _from_control_char(event: Any) -> Callable[[Any], str] | None:
    """Управляющие символы (часто не зависят от раскладки)."""
    ch = getattr(event, "char", "") or ""
    if ch == "\x01":
        return _select_all
    if ch == "\x03":
        return _copy
    if ch == "\x16":
        return _paste
    if ch == "\x18":
        return _cut
    return None


def _from_keycode(event: Any) -> Callable[[Any], str] | None:
    """Физический keycode при зажатом Ctrl/Cmd (удобно при RU раскладке)."""
    if not (_has_ctrl(event) or _has_cmd_darwin(event)):
        return None
    code = int(getattr(event, "keycode", 0) or 0)
    if code in (65, 0x41):
        return _select_all
    if code in (67, 0x43):
        return _copy
    if code in (86, 0x56):
        return _paste
    if code in (88, 0x58):
        return _cut
    return None


def _from_keysym(event: Any) -> Callable[[Any], str] | None:
    """Keysym при русской ЙЦУКЕН (физические A,C,V,X → ф,с,м,ч)."""
    if not (_has_ctrl(event) or _has_cmd_darwin(event)):
        return None
    ks = (getattr(event, "keysym", "") or "").lower()
    if ks in ("a", "ф"):
        return _select_all
    if ks in ("c", "с"):
        return _copy
    if ks in ("v", "м"):
        return _paste
    if ks in ("x", "ч"):
        return _cut
    return None


def _dispatch(w: Any, event: Any) -> str:
    """Обработка одного события клавиш."""
    for parser in (_from_control_char, _from_keycode, _from_keysym):
        fn = parser(event)
        if fn is not None:
            return fn(w)
    return ""


def enable_clipboard_bindings(widget: Any) -> None:
    """
    Включает Ctrl/Cmd+A, C, V, X и Shift+Insert для CTkEntry / CTkTextbox.

    Возвращает 'break' из обработчиков, где действие выполнено (без дублирования).
    """
    w = _resolve_inner(widget)
    if w is None:
        return

    def _on_key(event: Any) -> str:
        out = _dispatch(w, event)
        return out if out else ""

    w.bind("<Control-KeyPress>", _on_key, add="+")
    if sys.platform == "darwin":
        w.bind("<Command-KeyPress>", _on_key, add="+")

    w.bind("<Shift-Insert>", lambda _e: _paste(w), add="+")
