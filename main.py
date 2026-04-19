"""Точка входа: логирование и запуск GUI."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import Settings  # noqa: E402
from src.ui.app import PasswordManagerApp  # noqa: E402


def _setup_logging(settings: Settings) -> None:
    """Настраивает корневой логгер с ротацией файла."""
    log_path = settings.resolved_log_file()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.handlers.clear()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    fh = RotatingFileHandler(
        str(log_path),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


def main() -> None:
    """Запуск приложения."""
    settings = Settings()
    _setup_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Запуск приложения")
    app = PasswordManagerApp(settings)
    app.mainloop()


if __name__ == "__main__":
    main()
