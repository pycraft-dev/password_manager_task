# Локальный менеджер паролей

Десктопное приложение на **CustomTkinter** с шифрованием **AES-256-GCM**, хранением в **SQLite**, экспортом/импортом зашифрованного **JSON** и **импортом паролей из CSV** (экспорт Chrome / Яндекс.Браузер / Edge / Opera / Firefox). Один экран, тёмная тема, генератор паролей, локализация **RU/EN**.

## Скриншоты

Файлы лежат в [docs/screenshots/](docs/screenshots/).

### Экран мастер-пароля

![Экран входа с мастер-паролем](docs/screenshots/01-login.png)

### Список записей

![Главный экран со списком](docs/screenshots/02-main.png)

### Форма записи и генератор

![Форма записи и генератор пароля](docs/screenshots/03-form.png)

<details>
<summary>English version</summary>

# Local password manager

A **CustomTkinter** desktop app with **AES-256-GCM** encryption, **SQLite** storage, encrypted **JSON** export/import, and **CSV import** from browser password exports (Chrome / Yandex Browser / Edge / Opera / Firefox). Single-window UI, dark theme, password generator, **RU/EN** localization.

## Screenshots

![Login](docs/screenshots/01-login.png)

![Main list](docs/screenshots/02-main.png)

![Record form](docs/screenshots/03-form.png)

</details>

## Установка и запуск

1. Python **3.11+** (рекомендуется; проверено на 3.14 в среде разработки).
2. Клонируйте репозиторий и перейдите в каталог проекта.
3. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Скопируйте `.env.example` в `.env` и при необходимости измените пути:

```bash
copy .env.example .env
```

5. Запуск из корня проекта:

```bash
python main.py
```

### Сборка EXE (Windows)

```bash
pip install pyinstaller
pyinstaller build_exe.spec --noconfirm
```

Готовый файл: `dist/PasswordManager.exe`. Иконка и `translations.json` включаются через секцию `datas` в [build_exe.spec](build_exe.spec).

### Релиз (архив для клиента)

Текущая версия задаётся в [VERSION](VERSION), история изменений — в [CHANGELOG.md](CHANGELOG.md). Номер версии отображается в заголовке окна (`v…`).

Сборка EXE и ZIP с `LICENSE`, `README_КЛИЕНТУ.md`, `.env.example` и `CHANGELOG.md`:

```powershell
.\scripts\make_release.ps1
```

Архив появится в `release/PasswordManager-v<версия>-win64.zip`. Папка **`release/`** не коммитится в Git (см. `.gitignore`) — ZIP загружайте вручную в [GitHub Releases](https://docs.github.com/repositories/releasing-projects-on-github/about-releases) или отдельно клиенту.

### Публикация на GitHub

1. Создайте пустой репозиторий на GitHub (без README, если уже есть локальный).
2. В корне проекта: `git init`, затем `git add .` и `git commit -m "Initial commit"`.
3. Подключите remote и выполните `git push -u origin main` (или `master`).
4. В релиз на GitHub прикрепите архив из `release/`, собранный скриптом `make_release.ps1` — сам архив в репозиторий не кладётся.

В репозиторий не попадают: `dist/`, `build/`, `release/`, `.env`, `*.log`, локальные `*.db`, виртуальное окружение (см. [.gitignore](.gitignore)).

## Документация

- **Инструкция для пользователя:** [README_КЛИЕНТУ.md](README_КЛИЕНТУ.md)  
- **Тестовые данные:** [test_data/README.md](test_data/README.md)  

## Импорт из браузера (CSV)

1. Экспортируйте пароли из браузера в CSV (например, **Chrome:** «Настройки» → «Автозаполнение и пароли» → «Пароли Google» → меню «⋮» → **Экспорт паролей**).  
2. В приложении: **«Импорт из браузера»** → выберите тип браузера (формат CSV) → **«Обзор»** → укажите файл **.csv** или **.zip** (если браузер выдал архив с паролем — введите пароль ZIP и нажмите **«Открыть ZIP»**).  
3. Проверьте таблицу предпросмотра, при необходимости отфильтруйте **только новые** или **дубликаты**, снимите лишние галочки.  
4. Нажмите **«Импортировать выбранные»** или **«Импортировать все»**. Во время импорта доступны **прогресс** и кнопка **«Стоп»** (оставшиеся строки не добавляются).  
5. **Удалите CSV** с диска после импорта; файл приложением не сохраняется. Содержимое паролей в лог не пишется.

Для **ZIP** сначала используется стандартный модуль Python ``zipfile`` (часто хватает для экспорта Яндекс.Браузера и ZipCrypto). Если архив в формате **AES** и появится подсказка установить **pyzipper**, выполните ``pip install pyzipper`` (пакет уже указан в ``requirements.txt`` для сборки EXE).

**Форматы:** Chrome, **Яндекс.Браузер**, Edge и Opera — CSV Chromium (`name`, `url`, `username`, `password`); Firefox — колонки `url`, `username`, `password` (как в экспорте). Дубликаты определяются по **названию записи** (без учёта регистра), совпадающему с уже существующими в хранилище.

<details>
<summary>English: Browser CSV import</summary>

1. Export passwords to CSV from your browser (e.g. **Chrome:** Settings → Autofill and passwords → Google Passwords → ⋮ → **Export passwords**).  
2. In the app: **Import from browser** → pick the browser/format → **Browse** → select a **.csv** or **.zip** (if the browser exported a password-protected archive, enter the ZIP password and click **Open ZIP**).  
3. Review the preview table; use filters (**All / New only / Duplicates**) and row checkboxes.  
4. **Import selected** or **Import all**; use **Stop** to cancel the remaining rows.  
5. Delete the CSV after import; the app does not store it and does not log password contents.

For **ZIP**, the app tries Python’s built-in ``zipfile`` first (often enough for Yandex Browser / ZipCrypto). If the UI asks to install **pyzipper** (AES archives), run ``pip install pyzipper`` (listed in ``requirements.txt`` for the EXE build).

**Formats:** Chromium family (Chrome / Yandex Browser / Edge / Opera) uses `name,url,username,password`; Firefox uses `url,username,password`. Duplicates match existing entry **titles** case-insensitively.

</details>

### Безопасность (важно)

- Мастер-пароль **не хранится** на диске; из него выводится ключ **PBKDF2-HMAC-SHA256** (число итераций задаётся в `.env`, по умолчанию `390000`).
- Поля логина, пароля, заметок и пути вложения хранятся в SQLite в виде **зашифрованного blob** на запись. Название записи хранится **открытым текстом** для быстрого поиска (ограничение текущей версии).
- Экспорт — отдельный JSON, зашифрованный тем же мастер-паролем и **солью файла**; без пароля содержимое не прочитать.
- Демо не заменяет специализированные менеджеры паролей уровня продакшена; не храните реальные боевые секреты без отдельной оценки рисков.

### Автозапуск

Штатного автозапуска нет. Для автозапуска в Windows можно создать ярлык в папке «Автозагрузка» на `PasswordManager.exe`.

## Архитектура

```text
password_manager_task/
├── VERSION                 # номер релиза
├── main.py                 # точка входа, логирование
├── assets/                 # иконки
├── src/
│   ├── config/             # настройки и константы
│   ├── core/               # шифрование, БД, генератор, экспорт/импорт, импорт CSV
│   ├── ui/                 # окна, форма записи, панель импорта из браузера
│   └── utils/              # пути, парсинг CSV/ZIP, валидация, буфер обмена, i18n
├── test_data/              # примеры для ручных сценариев
├── tests/                  # pytest
└── translations.json       # строки RU/EN
```

Поток данных: мастер-пароль → PBKDF2 → ключ AES-GCM → шифрование полезной нагрузки каждой записи в SQLite.

## Лицензия

Проект распространяется по лицензии MIT: см. [LICENSE](LICENSE).

## Контакты разработчика

**Вова | pycraft-dev**  
Python-разработчик • Современные GUI-приложения • Автоматизация

- Электронная почта: [pycraft-dev@21051992.ru](mailto:pycraft-dev@21051992.ru)  
- Telegram: [@Pycraftdev](https://t.me/Pycraftdev)  
- Kwork: [kwork.ru/user/pycraft-dev](https://kwork.ru/user/pycraft-dev)  
- GitHub: [github.com/pycraft-dev](https://github.com/pycraft-dev)

> Нужно похожее приложение под ваши задачи? Напишите — обсудим.
