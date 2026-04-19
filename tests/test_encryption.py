"""Тесты шифрования."""

from __future__ import annotations

import os

import pytest

from src.core.encryption import (
    build_verifier_blob,
    derive_key_from_password,
    open_sealed,
    seal,
    verify_key,
)


def test_seal_roundtrip() -> None:
    key = os.urandom(32)
    plain = b"hello \xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82"
    blob = seal(plain, key)
    assert open_sealed(blob, key) == plain


def test_wrong_key_fails() -> None:
    key = os.urandom(32)
    wrong = os.urandom(32)
    blob = seal(b"secret", key)
    with pytest.raises(Exception):
        open_sealed(blob, wrong)


def test_pbkdf2_deterministic() -> None:
    salt = b"salt_test_123456"
    k1 = derive_key_from_password("pass", salt, 100_000)
    k2 = derive_key_from_password("pass", salt, 100_000)
    assert k1 == k2
    assert len(k1) == 32


def test_verifier() -> None:
    key = derive_key_from_password("master", os.urandom(16), 50_000)
    v = build_verifier_blob(key)
    assert verify_key(v, key) is True
    assert verify_key(v, os.urandom(32)) is False
