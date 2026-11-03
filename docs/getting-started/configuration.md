# Configuration

All configuration lives in NetBox's `configuration.py` under the `PLUGINS_CONFIG` dictionary. Every key is optional. A typical production setup only sets an encryption key, and optionally tunes the retries:

```python
PLUGINS = ["netbox_rir_manager"]

PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "encryption_key": "<a long random string, kept in your secrets manager>",
        "api_retry_count": 5,
        "api_retry_backoff": 4,
    },
}
```

Two other settings change how the plugin fits into NetBox: `top_level_menu` set to `False` lists its pages under NetBox's shared **Plugins** menu instead of a top-level **RIR Manager** menu, and `sync_interval_hours` sets the hours between scheduled syncs (24 by default).

Every setting, its default and how the plugin uses it are listed in [Reference: Settings](../reference/settings.md).

## Encryption and key rotation

`RIRUserKey.api_key` is stored using a Fernet ciphertext, prefixed with `$FERNET$`. The Fernet key is derived from the `encryption_key` setting (or NetBox's `SECRET_KEY` when the setting is empty) using HKDF-SHA256 with the salt `netbox-rir-manager` and info `api-key-encryption`. The derivation is implemented in `netbox_rir_manager/fields.py`.

Implications:

- **Pre-encryption rows are tolerated**: a value without the `$FERNET$` prefix is returned as-is. This lets the plugin work alongside data created before the `EncryptedCharField` was introduced.
- **Re-saving a row re-encrypts**: as soon as a `RIRUserKey` is saved, the value passes through `_encrypt` again and is stored in the new ciphertext.
- **Bad ciphertext yields the raw value**: if decryption raises `InvalidToken`, the field returns the stored string verbatim. This is intentional so that key rotation or accidental settings changes do not crash views.

!!! warning "Key rotation"

    Changing the `encryption_key` setting (or NetBox's `SECRET_KEY` when the plugin's setting is empty) makes all previously encrypted API keys unrecoverable. Decrypted reads silently fall through to the ciphertext on `InvalidToken`, which means write operations will fail at the RIR with confusing errors. Plan rotation as a coordinated event:

    1. Decrypt and re-encrypt all `RIRUserKey` rows (e.g. by reading and saving them) under the old key.
    2. Update the `encryption_key` setting.
    3. Re-enter the API keys for every user.

    Store the key alongside your database backups.
