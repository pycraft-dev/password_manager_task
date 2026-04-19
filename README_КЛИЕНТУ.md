# Менеджер паролей — для пользователя

## Что это

Программа для хранения логинов и паролей **на вашем компьютере**. Данные шифруются **мастер-паролем**, который вы придумываете сами. Интерфейс на русском и английском (переключатель **RU / EN**).

<details>
<summary>English</summary>

## What it is

A **local** password manager for your PC. Your data is encrypted with a **master password** you create. UI languages: Russian and English (**RU / EN** toggle).

</details>

## Как начать

1. Запустите `PasswordManager.exe` (или `python main.py`, если ставили из исходников).  
2. Если база ещё не создана: придумайте **мастер-пароль не короче 8 символов** и нажмите **«Создать хранилище»**.  
3. Если база уже есть: введите тот же мастер-пароль и нажмите **«Открыть»**.  
4. Добавляйте записи кнопкой **«Добавить»**, редактируйте и удаляйте выбранные.  

**Закрыть сессию:** кнопка **«Закрыть хранилище»** — вернётся экран ввода пароля.

<details>
<summary>English</summary>

1. Run the app.  
2. First run: create a **master password (8+ chars)** → **Create vault**.  
3. Next runs: **Unlock** with the same password.  
4. Use **Add / Edit / Delete** for entries. **Lock vault** returns to the login screen.

</details>

## Кнопки (главный экран)

| Кнопка | Действие |
|--------|----------|
| Добавить | Новая запись |
| Редактировать | Изменить выбранную |
| Удалить | Удалить выбранную (с подтверждением) |
| Поиск | Фильтр по названию |
| Экспорт | Сохранить зашифрованную копию |
| Импорт | Загрузить зашифрованную копию (дубликаты по названию пропускаются) |

Внизу отображается **число записей** и время **последнего сохранения** (локально).

<details>
<summary>English</summary>

| Button | Action |
|--------|--------|
| Add / Edit / Delete | Manage entries |
| Search | Filter by title |
| Export / Import | Encrypted backup; duplicate titles are skipped on import |

</details>

## Генератор пароля

В форме записи: длина **8–32**, опции символов, **Сгенерировать**, **Копировать**.

## Частые вопросы

**Забыл мастер-пароль — можно восстановить?**  
Нет. Без него данные не расшифровать.

**Где лежит база?**  
По умолчанию файл `encrypted.db` в папке с программой (или путь из `.env` для варианта из исходников).

**Можно ли прикрепить файл?**  
Можно выбрать путь к файлу на диске (вложение не копируется внутрь программы).

<details>
<summary>English FAQ</summary>

**Forgot master password?** Cannot recover.  
**Where is the database?** Default `encrypted.db` next to the app.  
**Attachments?** Only a file path is stored; the file is not copied into the vault.

</details>
