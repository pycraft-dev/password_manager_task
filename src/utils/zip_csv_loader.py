"""Извлечение CSV из ZIP-архива (stdlib ``zipfile``; при необходимости — ``pyzipper`` для AES)."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _safe_zip_member(name: str) -> bool:
    """Отсекает опасные имена внутри архива."""
    if ".." in name or name.startswith(("/", "\\")):
        return False
    return True


def _pick_csv_member(names: list[str]) -> str:
    """Выбирает CSV: приоритет имени с ``password``, иначе первый по алфавиту."""
    csv_names = [n for n in names if n.lower().endswith(".csv") and not n.endswith("/") and _safe_zip_member(n)]
    if not csv_names:
        raise ValueError("zip_no_csv")
    csv_names.sort(key=lambda s: (0 if "password" in s.lower() else 1, s.lower()))
    return csv_names[0]


def _decode_csv_blob(blob: bytes) -> str:
    return blob.decode("utf-8-sig", errors="replace")


def _extract_stdlib(zip_path: Path, password: str) -> str:
    """Читает CSV из ZIP через стандартную библиотеку (в т.ч. ZipCrypto с паролем)."""
    pwd_bytes = password.encode("utf-8") if password else None
    with zipfile.ZipFile(zip_path, "r") as zf:
        if pwd_bytes:
            zf.setpassword(pwd_bytes)
        member = _pick_csv_member(zf.namelist())
        blob = zf.read(member)
    return _decode_csv_blob(blob)


def _extract_pyzipper(zip_path: Path, password: str) -> str:
    """Читает CSV через pyzipper (AES и прочие случаи, где stdlib не справляется)."""
    import pyzipper

    with pyzipper.AESZipFile(zip_path, "r") as zf:
        if password:
            zf.setpassword(password.encode("utf-8"))
        member = _pick_csv_member(zf.namelist())
        blob = zf.read(member)
    return _decode_csv_blob(blob)


def extract_first_csv_text_from_zip(zip_path: Path, password: str) -> str:
    """
    Читает первый подходящий ``.csv`` из ZIP и возвращает его текст (UTF-8).

    Сначала используется :mod:`zipfile`; при ошибке (AES, нестандартное шифрование и т.п.)
    выполняется попытка через ``pyzipper``, если пакет установлен.

    Args:
        zip_path: путь к архиву.
        password: пароль в UTF-8; для незашифрованного ZIP — пустая строка.

    Raises:
        ValueError: коды ``zip_no_csv``, ``zip_bad_password``, ``zip_read_error``,
            ``zip_install_pyzipper`` (если нужен pyzipper, а модуля нет).
    """
    stdlib_error: BaseException | None = None
    try:
        return _extract_stdlib(zip_path, password)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        stdlib_error = exc
        logger.debug("ZIP через zipfile не удалось: %s", type(exc).__name__)

    try:
        return _extract_pyzipper(zip_path, password)
    except ValueError:
        raise
    except ImportError as exc:
        raise ValueError("zip_install_pyzipper") from (stdlib_error or exc)
    except RuntimeError as exc:
        logger.info("ZIP pyzipper: неверный пароль или сбой расшифровки")
        raise ValueError("zip_bad_password") from exc
    except Exception as exc:  # noqa: BLE001
        logger.info("ZIP pyzipper: ошибка чтения: %s", type(exc).__name__)
        raise ValueError("zip_read_error") from (stdlib_error or exc)
