from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django import forms
from django.conf import settings
from django.core.validators import URLValidator
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


class LenientURLValidator(URLValidator):
    """URLValidator that allows hostnames without a TLD (e.g. http://myhost:8000/)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Replace the host pattern to allow single-label hostnames
        import re

        # Rebuild the regex to accept hostnames without dots/TLDs
        self.regex = re.compile(
            r"^(?:[a-z0-9.+-]*)://"  # scheme
            r"(?:[^\s:@/]+(?::[^\s:@/]*)?@)?"  # user:pass@
            r"(?:"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)*[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)"  # hostname
            r"|localhost"
            r"|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # ipv4
            r"|\[?[A-F0-9]*:[A-F0-9:]+\]?"  # ipv6
            r")"
            r"(?::\d{1,5})?"  # port
            r"(?:[/?#][^\s]*)?"  # path/query/fragment
            r"\Z",
            re.IGNORECASE,
        )


class LenientURLFormField(forms.URLField):
    """Form URLField that accepts hostnames without a TLD."""

    default_validators = [LenientURLValidator()]


class LenientURLField(models.URLField):
    """URLField that accepts hostnames without a TLD."""

    default_validators = [LenientURLValidator()]

    def formfield(self, **kwargs):
        return super().formfield(**{"form_class": LenientURLFormField, **kwargs})


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
