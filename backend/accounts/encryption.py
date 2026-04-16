import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    key = getattr(settings, "PII_ENCRYPTION_KEY", "")
    if not key:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        ).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext):
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext):
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return ciphertext


class EncryptedCharField(models.CharField):
    """Transparently encrypts/decrypts a CharField value at rest."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_value(value) if value else value

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value) if value else value

    def to_python(self, value):
        if isinstance(value, str) and value:
            decrypted = decrypt_value(value)
            return decrypted
        return value


class HashedLookupField(models.CharField):
    """Stores a SHA-256 hash for indexed lookups of encrypted values."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()
        return value
