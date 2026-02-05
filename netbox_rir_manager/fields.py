from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db import models

_FERNET_PREFIX = "$FERNET$"
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        plugin_config = getattr(settings, "PLUGINS_CONFIG", {}).get("netbox_rir_manager", {})
        secret = plugin_config.get("encryption_key") or settings.SECRET_KEY
        derived = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=b"netbox-rir-manager",
            info=b"api-key-encryption",
        ).derive(secret.encode())
        _fernet_instance = Fernet(base64.urlsafe_b64encode(derived))
    return _fernet_instance


def _encrypt(value: str) -> str:
    if not value:
        return value
    if value.startswith(_FERNET_PREFIX):
        return value  # already encrypted
    token = _get_fernet().encrypt(value.encode())
    return f"{_FERNET_PREFIX}{token.decode()}"


def _decrypt(value: str) -> str:
    if not value:
        return value
    if not value.startswith(_FERNET_PREFIX):
        return value  # plaintext (pre-migration)
    token = value[len(_FERNET_PREFIX) :]
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return value


class EncryptedCharField(models.CharField):
    """CharField that encrypts values at rest using Fernet."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        return _encrypt(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _decrypt(value)
