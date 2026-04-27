# Configuration

Add overrides to `PLUGINS_CONFIG` in NetBox's `configuration.py`:

```python
PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "top_level_menu": True,
        "sync_interval_hours": 24,
        "auto_link_networks": True,
        "enabled_backends": ["ARIN"],
        "encryption_key": "",  # defaults to NetBox SECRET_KEY
        "api_retry_count": 3,
        "api_retry_backoff": 2,
    },
}
```

## Settings

| Setting | Default | Description |
|---|---|---|
| `top_level_menu` | `True` | Display RIR Manager as a top-level menu item in the NetBox navigation |
| `sync_interval_hours` | `24` | Interval in hours between scheduled background syncs |
| `auto_link_networks` | `True` | Automatically link synced RIR networks to matching NetBox Aggregates and Prefixes |
| `enabled_backends` | `["ARIN"]` | List of enabled RIR backends |
| `encryption_key` | `""` | Key used to encrypt API keys at rest. Falls back to NetBox's `SECRET_KEY` when empty |
| `api_retry_count` | `3` | Number of retries for failed RIR API calls |
| `api_retry_backoff` | `2` | Exponential backoff multiplier between API retries (in seconds) |

!!! warning "Key rotation"

    The `encryption_key` (or NetBox's `SECRET_KEY` if left empty) is used to encrypt stored API keys. **Changing or losing this key will make all previously encrypted API keys unrecoverable.** Store it securely and back it up alongside your database.
