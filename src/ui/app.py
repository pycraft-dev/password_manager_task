"""Главное окно приложения и переключение экранов."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image

from src.config.constants import COLOR_BG, COLOR_TEXT
from src.config.settings import Settings
from src.config.version import read_app_version
from src.core.database import PasswordDatabase
from src.ui.login_view import LoginView
from src.ui.main_window import MainWindow
from src.utils.assets import get_bundle_root, get_icon_path, get_project_root
from src.utils.i18n import load_translations

logger = logging.getLogger(__name__)


class PasswordManagerApp(ctk.CTk):
    """Одно окно: вход и основной интерфейс."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(fg_color=COLOR_BG)
        self._settings = settings
        self._db: PasswordDatabase | None = None
        self._master_password: str = ""
        self._tr = load_translations(_translations_path())
        self._login_view: LoginView | None = None
        self._main_view: MainWindow | None = None
        self._icon_ref: object | None = None
        self._version = read_app_version()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._set_window_title()
        self.geometry("920x680")
        self.minsize(400, 300)
        self.resizable(True, True)

        # Обычный фрейм: иначе CTkScrollableFrame поднимает нижнюю панель вверх области прокрутки.
        self._outer = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self._outer.pack(fill="both", expand=True)

        self._apply_window_icon()
        self._show_login()

    def _set_window_title(self) -> None:
        """Заголовок окна с версией."""
        self.title(f"{self._tr.t('app_title')}  v{self._version}")

    def _apply_window_icon(self) -> None:
        """Устанавливает иконку окна через CTkImage + PIL."""
        icon_path = get_icon_path()
        if not icon_path.exists():
            logger.warning("Иконка не найдена: %s", icon_path)
            return

        def _set_icon() -> None:
            try:
                img = Image.open(icon_path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
                self.iconphoto(True, ctk_img)
                self._icon_ref = ctk_img
            except Exception as exc:  # noqa: BLE001
                logger.exception("Не удалось установить иконку: %s", exc)

        self.after(100, _set_icon)

    def _on_language_changed(self) -> None:
        """Обновляет заголовок окна и дочерние экраны."""
        self._set_window_title()
        if self._login_view is not None and self._login_view.winfo_exists():
            self._login_view.refresh_language()
        if self._main_view is not None and self._main_view.winfo_exists():
            self._main_view.refresh_language()

    def _show_login(self) -> None:
        """Показывает экран мастер-пароля."""
        for w in self._outer.winfo_children():
            w.destroy()
        path = self._settings.resolved_database_path()
        is_new = not path.exists()
        self._login_view = LoginView(
            self._outer,
            self._tr,
            is_new,
            self._on_login_submit,
            self._on_language_changed,
        )
        self._login_view.pack(fill="both", expand=True)
        self._main_view = None

    def _on_login_submit(self, password: str) -> None:
        """Открывает БД после ввода мастер-пароля."""
        path = self._settings.resolved_database_path()
        try:
            db, _created = PasswordDatabase.open_or_create(
                path,
                password,
                self._settings.pbkdf2_iterations,
            )
        except ValueError:
            if self._login_view is not None:
                self._login_view.show_error(self._tr.t("err_unlock"))
            logger.info("Неверный мастер-пароль")
            return
        if self._db is not None:
            self._db.close()
        self._db = db
        self._master_password = password
        self._show_main()

    def _show_main(self) -> None:
        """Показывает список записей."""
        if self._db is None:
            return
        for w in self._outer.winfo_children():
            w.destroy()
        self._main_view = MainWindow(
            self._outer,
            self._db,
            self._settings,
            self._tr,
            self._master_password,
            on_lock=self._lock_vault,
            on_language_change=self._on_language_changed,
        )
        self._main_view.pack(fill="both", expand=True)
        self._login_view = None

    def _lock_vault(self) -> None:
        """Закрывает сессию и возвращает на экран входа."""
        if self._db is not None:
            self._db.close()
            self._db = None
        self._master_password = ""
        logger.info("Хранилище закрыто пользователем")
        self._show_login()


def _translations_path() -> Path:
    """Путь к translations.json (в сборке — из bundle)."""
    bundled = get_bundle_root() / "translations.json"
    if bundled.exists():
        return bundled
    return get_project_root() / "translations.json"
