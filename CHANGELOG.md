# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

## [1.0.1] — 2026-04-19

### Изменено

- Название приложения без пометки «демо»; EXE и архив релиза: `PasswordManager.exe` / `PasswordManager-<версия>-win64.zip`.

## [1.0.0] — 2026-04-19

### Добавлено

- Локальное хранилище SQLite с шифрованием AES-256-GCM и PBKDF2-HMAC-SHA256.
- Окно входа по мастер-паролю, список записей, форма с генератором пароля.
- Экспорт и импорт зашифрованного JSON.
- Локализация RU/EN (`translations.json`).
- Сборка Windows EXE (PyInstaller), иконка и ассеты в `datas`.
- Юнит-тесты (`pytest`) для шифрования, БД и экспорта.

### Исправлено

- Нижняя панель статуса и копирайт закреплены у нижнего края окна.
- После сохранения записи сброс прокрутки к списку; сброс фильтра поиска.
- Локализация кнопки «Закрыть хранилище» / Lock vault при смене языка.
- Горячие клавиши буфера: модуль `clipboard_bindings` (Ctrl/Cmd+A,C,V,X, Shift+Insert, русская раскладка).

---

## [1.0.1] — 2026-04-19 (EN)

### Changed

- Product name without “demo”; Windows binary `PasswordManager.exe`; release zip `PasswordManager-<version>-win64.zip`.

## [1.0.0] — 2026-04-19 (EN)

### Added

- SQLite vault with AES-256-GCM and PBKDF2-HMAC-SHA256.
- Master password login, entries list, record form with password generator.
- Encrypted JSON export/import.
- RU/EN localization.
- Windows EXE build (PyInstaller).

### Fixed

- Status bar pinned to the bottom; scroll reset after save; lock button i18n; clipboard bindings per updated project rules.
