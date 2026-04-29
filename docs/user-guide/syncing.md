# Syncing Resources

The plugin imports your RIR's view of an organization into NetBox: the org itself, its points of contact, every network allocated to it, and (where applicable) the customers attached to reassigned networks. Sync is one-way (RIR -> NetBox) and idempotent: rows are upserted by handle.

## Triggers

There are three ways to start a sync.

### Manual, single config

From an `RIRConfig` detail view, click **Sync**. The view enqueues a `SyncRIRConfigJob` for the requesting user and redirects back. The job runs under the RQ worker and writes a row to **Sync Logs** for every operation.

### Manual, bulk

From the `RIRConfig` list view, select rows and choose **Sync Selected**. The plugin enqueues one `SyncRIRConfigJob` per config. Configs without a `RIRUserKey` for the requesting user are skipped with a warning.

### Scheduled

`ScheduledRIRSyncJob` is registered as a NetBox system job at the daily interval. On each run it:

1. Iterates `RIRConfig.objects.filter(is_active=True)`.
2. For each config, picks the most-recently-used `RIRUserKey` (by checking which keys have synced-by relationships on `RIROrganization`, `RIRContact`, or `RIRNetwork`); falls back to the lowest-pk key for that config if no synced-by data exists.
3. Calls `sync_rir_config` with that key.
4. Logs failures per config and continues -- one failing config does not abort the rest.

Inspect or trigger it manually from **System > Background Jobs**.

## What gets synced

`sync_rir_config()` orchestrates three phases:

### 1. Organization

`backend.get_organization(rir_config.org_handle)` is called. The result populates an `RIROrganization` row, upserted by `handle`. The org's address is normalised into an `RIRAddress` (deduplicated against existing addresses).

### 2. Contacts (POCs)

For every `poc_link` in the org's raw payload, `backend.get_poc(handle)` is called. Each POC becomes an `RIRContact` row (upserted by handle), linked back to the org. Contact addresses are also normalised into `RIRAddress` rows.

The `contact_type` is one of `PERSON` or `ROLE` (per `ContactTypeChoices`).

### 3. Networks (and customers)

The plugin iterates `Aggregate.objects.filter(rir=rir_config.rir)`. For each NetBox aggregate:

1. Compute the aggregate's start/end IPv4 or IPv6 addresses.
2. Call `backend.find_net(start, end)` to locate the matching ARIN Net.
3. Upsert an `RIRNetwork` row (by handle) and link it to the aggregate.
4. If the Net has a `customer_handle`, fetch and upsert the matching `RIRCustomer`.

After the per-config job finishes, `SyncRIRConfigJob` enqueues one `SyncPrefixesJob` per `(aggregate, parent_net)` pair. That job walks every `Prefix` contained in the aggregate, calls `find_net` for each, and creates an `RIRNetwork` row whenever the result is a different handle from the parent (i.e. a real reassignment, not the parent net leaking through).

## Auto-linking

When `auto_link_networks` is `True` (the default), a post-save signal on `RIRNetwork` reads the `net_blocks` from `raw_data` and tries to match them against existing NetBox `Aggregate` and `Prefix` records by exact CIDR. The first match wins and the FK is populated; existing links are not overwritten.

The signal lives in `netbox_rir_manager/signals.py` (`auto_link_network`). Disable it by setting `auto_link_networks = False`.

## Sync logs

Every sync operation writes one row to `RIRSyncLog`:

| Field            | Notes                                                                                         |
|------------------|-----------------------------------------------------------------------------------------------|
| `rir_config`     | The config being synced.                                                                      |
| `operation`      | One of `sync`, `create`, `update`, `delete`, `reassign`, `reallocate`, `remove`.              |
| `object_type`    | `organization`, `contact`, `network`, `customer`.                                             |
| `object_handle`  | The RIR-side handle (or NetBox prefix string for `skipped` netting cases).                    |
| `status`         | `success`, `error`, or `skipped`.                                                             |
| `message`        | Human-readable summary (e.g. `Created network NET-198-51-100-0-1`).                           |

Browse them under **RIR Manager > Sync Logs**, filter by config or status, or read them via `/api/plugins/rir-manager/sync-logs/`.

## What is **not** synced

- ASN allocations. `RIRBackend.get_asn` exists for backend implementations but the ARIN backend currently returns `None` and the orchestrator does not call it.
- Backend-specific sync (`backend.sync_resources`) is a stub on the ARIN backend (`return []`); the orchestrator drives the read pipeline directly via `get_organization`, `get_poc`, and `find_net`.

## Failure modes

- **No API key for the requesting user**: the manual sync view shows an error and redirects without enqueueing.
- **`backend.get_organization` returns `None`**: `RIRSyncLog` row with status `error`, `object_type=organization`. The job continues but skips contacts and networks for that config.
- **`backend.find_net` returns `None`**: no log row by default (the aggregate has no ARIN counterpart). Manual aggregate-level sync writes a `skipped` log row in this case for traceability.
- **Transient connection errors**: `tenacity` retries up to `api_retry_count` times with exponential backoff capped at `api_retry_backoff * api_retry_count` seconds. Permanent failures bubble up as `None` and are logged.

## See also

- [IPAM Integration](ipam-integration.md) -- the **Sync** buttons on Aggregate and Prefix pages.
- [Reference: Background Jobs](../reference/jobs.md) -- the full lifecycle of `SyncRIRConfigJob`, `SyncPrefixesJob`, `ScheduledRIRSyncJob`.
