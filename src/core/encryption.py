"""PBKDF2 и AES-256-GCM для хранилища."""

from __future__ import annotations

import logging
import os
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

_NONCE_LEN: Final[int] = 12


def derive_key_from_password(
    password: str,
    salt: bytes,
    iterations: int,
) -> bytes:
    """
    Выводит 32-байтовый ключ AES-256 из мастер-пароля и соли PBKDF2-HMAC-SHA256.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def seal(plaintext: bytes, key: bytes) -> bytes:
    """
    Шифрует данные AES-256-GCM. Возвращает nonce || ciphertext (с tag в конце по API cryptography).
    """
    aes = AESGCM(key)
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = aes.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def open_sealed(blob: bytes, key: bytes) -> bytes:
    """
    Расшифровывает blob, созданный функцией seal. Бросает исключение при неверном ключе или повреждении.
    """
    if len(blob) < _NONCE_LEN + 16:
        raise ValueError("Слишком короткий шифротекст")
    nonce = blob[:_NONCE_LEN]
    ct = blob[_NONCE_LEN:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ct, None)


def build_verifier_blob(key: bytes) -> bytes:
    """Создаёт зашифрованный маркер для проверки мастер-пароля при открытии хранилища."""
    return seal(b"VAULT_VERIFIER_V1", key)


def verify_key(verifier_blob: bytes, key: bytes) -> bool:
    """Проверяет, что ключ подходит к сохранённому verifier."""
    try:
        return open_sealed(verifier_blob, key) == b"VAULT_VERIFIER_V1"
    except Exception as exc:  # noqa: BLE001
        logger.info("Проверка ключа не пройдена: %s", type(exc).__name__)
        return False
