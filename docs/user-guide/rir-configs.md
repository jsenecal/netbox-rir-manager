# RIR Configs

An **RIR Config** binds the plugin to a specific RIR account. It is the parent object every other plugin model hangs off of: user keys, synced organisations and contacts, networks, customers, sync logs, tickets, and the daily scheduled job all point at one `RIRConfig`.

## Fields

| Field        | Type                       | Description                                                                                  |
|--------------|----------------------------|----------------------------------------------------------------------------------------------|
| `rir`        | FK to `ipam.RIR`           | The NetBox RIR this config targets. Required. Combined with `name` for uniqueness.            |
| `name`       | string (max 100)           | Free-form label, e.g. `production-arin` or `ote`. Unique per RIR.                             |
| `api_url`    | URL (lenient)              | Override the backend's default endpoint. Leave blank to use the backend's built-in URL. Hostnames without a TLD (e.g. `http://reg-mock:8080/`) are accepted. |
| `org_handle` | string (max 50)            | Your account's primary org handle at the RIR (e.g. `EXAMPLE-1` for ARIN). Used by `authenticate()` and `sync_resources`. |
| `is_active`  | boolean                    | The scheduled sync only iterates active configs. Inactive configs remain editable.            |
| `last_sync`  | datetime                   | Stamped by `sync_rir_config` on completion. Read-only.                                        |

The model also inherits `tags`, `created`, and `last_updated` from `NetBoxModel`, and tracks asynchronous jobs via the `JobsMixin` (visible on the **Jobs** tab of the detail view).

## Creating a config

1. Go to **RIR Manager > Configs** and click **Add**.
2. Pick the RIR.
3. Set a name unique within that RIR.
4. Optional: set `api_url` to point at a non-production endpoint (ARIN OT&E is `https://reg.ote.arin.net/regrws/`).
5. Set `org_handle`. Most operations need this -- ARIN's `authenticate()` short-circuits to `False` if it is empty.
6. Save.

## Bulk operations

The list view supports the standard NetBox bulk actions plus one custom action:

- **Add**: standard create form.
- **Import**: CSV import via `RIRConfigImportForm`. Fields: `rir` (looked up by name), `name`, `api_url`, `org_handle`, `is_active`.
- **Edit**: bulk-edit `rir`, `api_url`, `org_handle`, and `is_active`.
- **Sync Selected**: enqueue a `SyncRIRConfigJob` for every selected config. Configs without a user key for the requesting user are skipped with a warning. See [Syncing Resources](syncing.md).
- **Delete**: standard bulk delete. Cascades through every dependent plugin model.

## What happens when a config is deleted

`RIRConfig` is the parent of every other plugin model that holds RIR data. Deleting it cascades through:

- `RIRUserKey` (per-user credentials)
- `RIROrganization`, `RIRContact`, `RIRNetwork`, `RIRCustomer`
- `RIRSyncLog`, `RIRTicket`

The corresponding `ipam.Aggregate` and `ipam.Prefix` rows are unaffected -- the foreign key from `RIRNetwork` to those is `SET_NULL`.

## REST API

```http
GET  /api/plugins/rir-manager/configs/
POST /api/plugins/rir-manager/configs/
GET  /api/plugins/rir-manager/configs/{id}/
PATCH /api/plugins/rir-manager/configs/{id}/
DELETE /api/plugins/rir-manager/configs/{id}/
```

See the [REST API reference](../reference/rest-api.md) for filtering and pagination.

## Related

- [User API Keys](user-api-keys.md) -- attach a credential to a config.
- [Syncing Resources](syncing.md) -- run a sync against a config.
- [Reference: Models](../reference/models.md) -- full model field listing.
