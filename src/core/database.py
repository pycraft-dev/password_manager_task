"""SQLite-хранилище записей с шифрованием полезной нагрузки."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.core.encryption import (
    build_verifier_blob,
    derive_key_from_password,
    open_sealed,
    seal,
    verify_key,
)

logger = logging.getLogger(__name__)

_META_SALT = "salt"
_META_VERIFIER = "verifier"


@dataclass(frozen=True)
class EntryRecord:
    """Расшифрованная запись пароля."""

    id: int | None
    title: str
    login: str
    password: str
    notes: str
    attachment_path: str
    created_at: str
    updated_at: str


class PasswordDatabase:
    """Операции CRUD над зашифрованными записями."""

    def __init__(
        self,
        db_path: Path,
        conn: sqlite3.Connection,
        master_key: bytes,
        iterations: int,
    ) -> None:
        self._path = db_path
        self._conn = conn
        self._key = master_key
        self._iterations = iterations
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Закрывает соединение с БД."""
        self._conn.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Сырое соединение (для тестов)."""
        return self._conn

    @classmethod
    def open_or_create(
        cls,
        db_path: Path,
        master_password: str,
        iterations: int,
    ) -> tuple["PasswordDatabase", bool]:
        """
        Открывает или создаёт БД. Возвращает (database, created_new).

        Raises:
            ValueError: если пароль неверный для существующего хранилища.
        """
        is_new = not db_path.exists()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            _init_schema(conn)
            if is_new:
                salt = os.urandom(16)
                key = derive_key_from_password(master_password, salt, iterations)
                verifier = build_verifier_blob(key)
                _set_meta(conn, _META_SALT, salt)
                _set_meta(conn, _META_VERIFIER, verifier)
                conn.commit()
                logger.info("Создано новое хранилище: %s", db_path)
                return cls(db_path, conn, key, iterations), True

            salt = _get_meta_required(conn, _META_SALT)
            verifier = _get_meta_required(conn, _META_VERIFIER)
            key = derive_key_from_password(master_password, salt, iterations)
            if not verify_key(verifier, key):
                conn.close()
                raise ValueError("Неверный мастер-пароль")
            conn.commit()
            logger.info("Хранилище открыто: %s", db_path)
            return cls(db_path, conn, key, iterations), False
        except Exception:
            conn.close()
            raise

    def _encrypt_payload(self, data: dict[str, Any]) -> bytes:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        return seal(raw, self._key)

    def _decrypt_payload(self, blob: bytes) -> dict[str, Any]:
        raw = open_sealed(blob, self._key)
        return json.loads(raw.decode("utf-8"))

    def add_entry(
        self,
        title: str,
        login: str,
        password: str,
        notes: str,
        attachment_path: str,
    ) -> int:
        """Добавляет запись. Возвращает id."""
        now = _utc_now_iso()
        payload = {
            "login": login,
            "password": password,
            "notes": notes,
            "attachment_path": attachment_path,
        }
        blob = self._encrypt_payload(payload)
        cur = self._conn.execute(
            """
            INSERT INTO entries (title, payload_enc, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (title.strip(), blob, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_entry(
        self,
        entry_id: int,
        title: str,
        login: str,
        password: str,
        notes: str,
        attachment_path: str,
    ) -> None:
        """Обновляет запись по id."""
        now = _utc_now_iso()
        payload = {
            "login": login,
            "password": password,
            "notes": notes,
            "attachment_path": attachment_path,
        }
        blob = self._encrypt_payload(payload)
        self._conn.execute(
            """
            UPDATE entries
            SET title = ?, payload_enc = ?, updated_at = ?
            WHERE id = ?
            """,
            (title.strip(), blob, now, entry_id),
        )
        self._conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        """Удаляет запись."""
        self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._conn.commit()

    def get_entry(self, entry_id: int) -> EntryRecord | None:
        """Возвращает расшифрованную запись или None."""
        row = self._conn.execute(
            "SELECT id, title, payload_enc, created_at, updated_at FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_entries(self, title_query: str | None = None) -> list[EntryRecord]:
        """Список записей, опционально фильтр по подстроке в title (без учёта регистра)."""
        if title_query and title_query.strip():
            like = f"%{title_query.strip().lower()}%"
            rows = self._conn.execute(
                """
                SELECT id, title, payload_enc, created_at, updated_at
                FROM entries
                WHERE lower(title) LIKE ?
                ORDER BY title COLLATE NOCASE
                """,
                (like,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, title, payload_enc, created_at, updated_at
                FROM entries
                ORDER BY title COLLATE NOCASE
                """,
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count_entries(self) -> int:
        """Число записей."""
        row = self._conn.execute("SELECT COUNT(*) AS c FROM entries").fetchone()
        return int(row["c"]) if row else 0

    def title_exists(self, title: str, exclude_id: int | None = None) -> bool:
        """Проверяет уникальность названия (без учёта регистра)."""
        t = title.strip().lower()
        if exclude_id is None:
            row = self._conn.execute(
                "SELECT 1 FROM entries WHERE lower(title) = ? LIMIT 1",
                (t,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT 1 FROM entries WHERE lower(title) = ? AND id != ? LIMIT 1",
                (t, exclude_id),
            ).fetchone()
        return row is not None

    def _row_to_record(self, row: sqlite3.Row) -> EntryRecord:
        inner = self._decrypt_payload(row["payload_enc"])
        return EntryRecord(
            id=int(row["id"]),
            title=str(row["title"]),
            login=str(inner.get("login", "")),
            password=str(inner.get("password", "")),
            notes=str(inner.get("notes", "")),
            attachment_path=str(inner.get("attachment_path", "")),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def export_plain_records(self) -> list[dict[str, Any]]:
        """Список словарей для экспорта (все поля открытым текстом в памяти)."""
        out: list[dict[str, Any]] = []
        for rec in self.list_entries():
            out.append(
                {
                    "title": rec.title,
                    "login": rec.login,
                    "password": rec.password,
                    "notes": rec.notes,
                    "attachment_path": rec.attachment_path,
                    "created_at": rec.created_at,
                    "updated_at": rec.updated_at,
                }
            )
        return out

    def import_records_skip_duplicate_titles(
        self,
        records: Iterable[dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Импортирует записи. Дубликаты по названию пропускаются.
        Возвращает (импортировано, пропущено).
        """
        imported = 0
        skipped = 0
        for item in records:
            title = str(item.get("title", "")).strip()
            if not title:
                skipped += 1
                continue
            if self.title_exists(title):
                skipped += 1
                continue
            self.add_entry(
                title=title,
                login=str(item.get("login", "")),
                password=str(item.get("password", "")),
                notes=str(item.get("notes", "")),
                attachment_path=str(item.get("attachment_path", "")),
            )
            imported += 1
        return imported, skipped


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vault_meta (
            name TEXT PRIMARY KEY NOT NULL,
            value BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            payload_enc BLOB NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entries_title_lower ON entries (lower(title));
        """
    )


def _set_meta(conn: sqlite3.Connection, name: str, value: bytes) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO vault_meta (name, value) VALUES (?, ?)",
        (name, value),
    )


def _get_meta_required(conn: sqlite3.Connection, name: str) -> bytes:
    row = conn.execute(
        "SELECT value FROM vault_meta WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Отсутствует метаданные: {name}")
    return bytes(row["value"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
