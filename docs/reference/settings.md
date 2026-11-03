# Settings

The plugin reads its settings from `PLUGINS_CONFIG["netbox_rir_manager"]` in NetBox's `configuration.py`. Every key is optional. The defaults below are the `default_settings` declared in `netbox_rir_manager/__init__.py`.

For a worked example and the encryption and retry background, see [Configuration](../getting-started/configuration.md).

## Summary

| Setting                    | Default       | Read by the plugin |
|----------------------------|---------------|--------------------|
| `auto_link_networks`       | `True`        | Yes                |
| `encryption_key`           | `""`          | Yes                |
| `api_retry_count`          | `3`           | Yes                |
| `api_retry_backoff`        | `2`           | Yes                |
| `geocoding_provider`       | `"nominatim"` | Yes                |
| `top_level_menu`           | `True`        | No                 |
| `sync_interval_hours`      | `24`          | No                 |
| `enabled_backends`         | `["ARIN"]`    | No                 |
| `google_geocoding_api_key` | `""`          | No                 |

The settings marked "No" are declared but no code reads them. Changing them has no effect in this release.

## Settings in use

### `auto_link_networks`

Default: `True`. Read by the `auto_link_network` post-save signal in `netbox_rir_manager/signals.py`.

Each time an `RIRNetwork` is saved, the signal reads the `net_blocks` stored in its `raw_data`. For each block in turn, it looks for a NetBox `Aggregate` with exactly that CIDR, then a `Prefix`, and links the network to the first match. A network that already has an aggregate or a prefix is left alone. Set the value to `False` to turn this off.

### `encryption_key`

Default: `""`. Read by `netbox_rir_manager/fields.py` to derive the Fernet key that encrypts `RIRUserKey.api_key`.

An empty value falls back to NetBox's `SECRET_KEY`. The derived key is cached for the life of the process, so restart NetBox and the RQ worker after changing it. Changing it makes every stored API key unreadable; see [Encryption and key rotation](../getting-started/configuration.md#encryption-and-key-rotation).

### `api_retry_count`

Default: `3`. Read by `ARINBackend._call_with_retry` in `netbox_rir_manager/backends/arin.py`.

The total number of attempts for a call to ARIN that raises `ConnectionError`, `OSError` or `TimeoutError`. When every attempt fails, the call returns `None`. An error response from ARIN is not retried.

### `api_retry_backoff`

Default: `2`. Read alongside `api_retry_count`.

The wait between attempts grows exponentially (`tenacity.wait_exponential(multiplier=1)`) and is capped at `api_retry_backoff * api_retry_count` seconds.

### `geocoding_provider`

Default: `"nominatim"`. Read by `_get_geocoding_service` in `netbox_rir_manager/services/geocoding.py`.

`"nominatim"` selects OpenStreetMap Nominatim through `geopy`. It is the only provider implemented, and any other value also falls back to Nominatim. See [Addresses and Geocoding](../user-guide/addresses.md).

## Declared but unused

### `top_level_menu`

Default: `True`. Not read. The plugin always registers **RIR Manager** as its own top-level menu (`netbox_rir_manager/navigation.py`).

### `sync_interval_hours`

Default: `24`. Not read. `ScheduledRIRSyncJob` is registered with a fixed daily interval; see [Background Jobs](jobs.md).

### `enabled_backends`

Default: `["ARIN"]`. Not read. Views and jobs construct the ARIN backend directly; see [Backends](backends.md).

### `google_geocoding_api_key`

Default: `""`. Not read. There is no Google geocoding provider.
