# Background Jobs

The plugin's background work runs as NetBox jobs (`JobRunner` subclasses in `netbox_rir_manager/jobs.py`) on the RQ worker, so `manage.py rqworker` must be running. Every job except the scheduled sync is attached to an `RIRConfig` and listed on that config's **Jobs** tab; all of them appear under **System > Background Jobs**.

| Job name             | Class                 | Queued by                                                      |
|----------------------|-----------------------|----------------------------------------------------------------|
| `RIR Sync`           | `SyncRIRConfigJob`    | **Sync** and **Sync Selected** on RIR configs, and `POST /api/plugins/rir-manager/configs/{id}/sync/` |
| `ARIN Prefix Sync`   | `SyncPrefixesJob`     | `RIR Sync` and `Scheduled RIR Sync`, one per synced aggregate   |
| `ARIN Reassign`      | `ReassignJob`         | Saving a prefix under an allocation with **Auto reassign** set  |
| `ARIN Remove`        | `RemoveNetworkJob`    | Deleting or deactivating a prefix under an allocation with **Auto reassign** set |
| `Scheduled RIR Sync` | `ScheduledRIRSyncJob` | NetBox's system job scheduler, every `sync_interval_hours`     |

Jobs queued from a user's action, or from a prefix edit, run as a NetBox user, and the changes they make are recorded in the changelog under that user. `Scheduled RIR Sync` is a system job with no user, so the changes it makes itself are not recorded in the changelog; the `ARIN Prefix Sync` jobs it queues run as the owner of the config's default key. Which RIR key each job uses is described in [Which key an operation uses](../user-guide/user-api-keys.md#which-key-an-operation-uses).

## RIR Sync

Syncs one config: its organization, the organization's contacts, and the networks anchoring the config's aggregates, as described in [Syncing Resources](../user-guide/syncing.md). It then queues one `ARIN Prefix Sync` per aggregate it linked.

- **User**: the user who asked for the sync.
- **Key**: that user's own key on the config. With none, the job records `status: error` and `message: No API key` in its data and syncs nothing.
- **Job data**: `rir_config` (the config name) and `sync_logs_count`, the number of sync log rows the run wrote.

The config's `last_sync` is set when the sync finishes.

## ARIN Prefix Sync

Discovers reassignments beneath one aggregate. For every NetBox prefix inside the aggregate, it asks ARIN for the most specific network covering the prefix. When ARIN returns a network other than the parent allocation, the job creates or updates that `RIRNetwork`, links it to the prefix, writes a `success` sync log row and syncs the network's customer.

- **User and key**: the user and key the parent sync used. For the scheduled sync, that is the config's default key and the user who owns it.

## ARIN Reassign

Reassigns one prefix automatically; see [Automatic reassignment and removal](../user-guide/write-operations.md#automatic-reassignment-and-removal). Manual reassignments from a form or the REST API are sent directly and do not use this job.

1. Finds the parent allocation with **Auto reassign** set on an active config. Without one, the job stops with an error.
2. Asks ARIN what covers the prefix. If it is already a network other than the parent, the job syncs that network to the prefix, writes a `skipped` sync log row and stops without reassigning.
3. Chooses a **detailed** reassignment to the organization when the prefix's tenant is linked to an `RIROrganization`, and a **simple** one otherwise. A simple reassignment needs the prefix's Site and its address; see [Addresses and Geocoding](../user-guide/addresses.md).
4. Submits the reassignment, with a net name built from the tenant and the prefix (see [Network names](../user-guide/write-operations.md#network-names)).

- **User and key**: the user who saved the prefix, with their own key on the config. When no user is behind the change (automation outside a web or API request), the config's default key and the user who owns it.
- **Job data**: `prefix`, `status` (`success`, `synced` or `error`), `message`, `reassignment_type` (`simple` or `detailed`), `org_handle` for a detailed reassignment, and `ticket_number` when ARIN opened a ticket.

## ARIN Remove

Removes one reassigned or reallocated network at ARIN when its prefix is deleted or no longer Active.

- **User and key**: as for `ARIN Reassign`: the user who edited the prefix and their own key, or the default key outside a request.
- **Job data**: `network_handle` and `status` (`success` or `error`); on failure, `message` holds the error, with ARIN's reason when ARIN refused the removal.

## Scheduled RIR Sync

A NetBox system job registered when the plugin loads, at the interval set by [`sync_interval_hours`](settings.md#sync_interval_hours) (24 hours by default), so restart the RQ worker after installing or upgrading the plugin or changing the setting. It syncs every active config with the config's default key and queues the same `ARIN Prefix Sync` jobs as a manual sync; see [Scheduled](../user-guide/syncing.md#scheduled) for the details.

- **User**: none. The changes it makes itself are not recorded in the changelog.
- **Job data**: `configs_synced` (the number of active configs) and `total_logs`, the number of sync log rows written.

Its runs are listed under **System > Background Jobs**.
