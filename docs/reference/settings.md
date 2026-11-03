# Settings

The plugin reads its settings from `PLUGINS_CONFIG["netbox_rir_manager"]` in NetBox's `configuration.py`. Every key is optional. The defaults below are the `default_settings` declared in `netbox_rir_manager/__init__.py`.

For a minimal setup and how to rotate the encryption key, see [Configuration](../getting-started/configuration.md).

## Summary

| Setting               | Default       |
|-----------------------|---------------|
| `top_level_menu`      | `True`        |
| `sync_interval_hours` | `24`          |
| `auto_link_networks`  | `True`        |
| `encryption_key`      | `""`          |
| `api_retry_count`     | `3`           |
| `api_retry_backoff`   | `2`           |
| `geocoding_provider`  | `"nominatim"` |

## Settings

### `top_level_menu`

Default: `True`. Read by `netbox_rir_manager/navigation.py` when NetBox loads the plugin.

With `True`, the plugin registers its own top-level **RIR Manager** menu, with its items grouped under **Configs**, **Resources** and **Operations**. With `False`, the same items are listed, without the groups, under the **NetBox RIR Manager** section of NetBox's shared **Plugins** menu. Restart NetBox after changing it.

### `sync_interval_hours`

Default: `24`. Read by `netbox_rir_manager/jobs.py` when the plugin loads, to register `ScheduledRIRSyncJob` as a NetBox system job.

The number of hours between two runs of the scheduled sync. It must be a whole number of hours, at least `1`; any other value stops NetBox from starting with an `ImproperlyConfigured` error. The RQ worker schedules the job when it starts, so restart it after changing the value. If a run is already scheduled at the old interval, the worker deletes it and enqueues a replacement at the new interval without a scheduled time, so a sync runs as soon as the worker restarts and the following runs come every `sync_interval_hours` hours. See [Background Jobs](jobs.md#scheduled-rir-sync).

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

Increase `api_retry_count` if transient network errors interrupt scheduled syncs, and `api_retry_backoff` to spread retries further apart on rate-limited connections.

### `geocoding_provider`

Default: `"nominatim"`. Read by `_get_geocoding_service` in `netbox_rir_manager/services/geocoding.py`.

`"nominatim"` selects OpenStreetMap Nominatim through `geopy`. It is the only provider implemented, and any other value also falls back to Nominatim. See [Addresses and Geocoding](../user-guide/addresses.md).
