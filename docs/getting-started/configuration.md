# Configuration

All configuration lives in NetBox's `configuration.py` under the `PLUGINS_CONFIG` dictionary. Every key is optional -- the defaults match what the plugin uses internally.

```python
PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "top_level_menu": True,
        "sync_interval_hours": 24,
        "auto_link_networks": True,
        "enabled_backends": ["ARIN"],
        "encryption_key": "",  # falls back to NetBox SECRET_KEY
        "api_retry_count": 3,
        "api_retry_backoff": 2,
        "geocoding_provider": "nominatim",
        "google_geocoding_api_key": "",
    },
}
```

## Settings reference

| Setting                    | Default       | Description                                                                                       |
|----------------------------|---------------|---------------------------------------------------------------------------------------------------|
| `top_level_menu`           | `True`        | Render **RIR Manager** as a top-level menu item in the NetBox sidebar.                            |
| `sync_interval_hours`      | `24`          | Cadence (hours) for the daily `ScheduledRIRSyncJob`. The job interval is fixed daily today; the value is reserved for future use. |
| `auto_link_networks`       | `True`        | Auto-link freshly synced `RIRNetwork` records to `ipam.Aggregate` and `ipam.Prefix` based on `net_blocks` in the raw RIR payload. |
| `enabled_backends`         | `["ARIN"]`    | Backend names the plugin will activate. Values must match a registered `RIRBackend.name`.         |
| `encryption_key`           | `""`          | Secret used to derive the Fernet key that encrypts `RIRUserKey.api_key`. Empty falls back to NetBox `SECRET_KEY`. |
| `api_retry_count`          | `3`           | Number of attempts for transient failures (`ConnectionError`, `OSError`, `TimeoutError`) when calling the RIR. |
| `api_retry_backoff`        | `2`           | Cap (seconds) for exponential backoff between retries. Effective wait is `min(2^attempt, backoff * api_retry_count)`. |
| `geocoding_provider`       | `"nominatim"` | Geocoding service used to resolve Site addresses. Currently only `nominatim` is implemented; unknown values fall back to Nominatim. |
| `google_geocoding_api_key` | `""`          | Reserved for a future Google Maps geocoding backend. Has no effect today.                         |

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

## Backends

`enabled_backends` is a list of names to register at startup. Backends self-register via the `@register_backend` decorator in `netbox_rir_manager/backends/__init__.py`; the setting controls which appear in user-facing forms. Today the only built-in option is `"ARIN"`. See [Reference: Backends](../reference/backends.md) and [Adding a Backend](../development/adding-a-backend.md).

## API retries

Each call into `pyregrws` is wrapped in a `tenacity.Retrying` block that retries on `ConnectionError`, `OSError`, and `TimeoutError`. ARIN HTTP errors (returned as `regrws.models.Error`) are **not** retried; they are surfaced as `None` to the caller and recorded as `RIRSyncLog` entries with status `error`.

The exponential backoff is configured as:

```python
wait_exponential(multiplier=1, max=api_retry_backoff * api_retry_count)
```

Tuning notes:

- Increase `api_retry_count` if you frequently see transient network blips during scheduled syncs.
- Increase `api_retry_backoff` to spread retries further apart on rate-limited connections.

## Geocoding

When a NetBox `Site` has a `physical_address` or `latitude`/`longitude`, the plugin can resolve it to a structured `RIRAddress` automatically. The default provider is OpenStreetMap Nominatim via `geopy`. State and province names are mapped to ISO-3166-2 subdivision codes via `pycountry`.

Set `geocoding_provider = "nominatim"` (the default) or leave it unset. Other values are reserved for future backends. Nominatim has a strict usage policy; see [Addresses and Geocoding](../user-guide/addresses.md) for guidance.

## A minimal production config

```python
PLUGINS = ["netbox_rir_manager"]

PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "enabled_backends": ["ARIN"],
        "encryption_key": "<a long random string, kept in your secrets manager>",
        "api_retry_count": 5,
        "api_retry_backoff": 4,
    },
}
```

The full per-setting reference, including how each value is consumed at runtime, lives in [Reference: Settings](../reference/settings.md).
