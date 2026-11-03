# REST API

Every model and action is exposed via NetBox's REST API under `/api/plugins/rir-manager/`.

## Endpoints

| Endpoint                                       | Resource                          |
|------------------------------------------------|-----------------------------------|
| `/api/plugins/rir-manager/configs/`            | RIR configurations                |
| `/api/plugins/rir-manager/user-keys/`          | Per-user API keys                 |
| `/api/plugins/rir-manager/organizations/`      | RIR organizations                 |
| `/api/plugins/rir-manager/contacts/`           | RIR contacts (POCs)               |
| `/api/plugins/rir-manager/networks/`           | RIR networks                      |
| `/api/plugins/rir-manager/sync-logs/`          | Sync operation logs               |
| `/api/plugins/rir-manager/tickets/`            | RIR tickets                       |

## Triggering a sync

```
POST /api/plugins/rir-manager/configs/{id}/sync/
```

Queues the same background sync as the **Sync** button on the config page
(`SyncRIRConfigJob`): the organization, its contacts and the aggregate-level
networks, then one prefix-discovery job per aggregate. The request takes no body.
The job runs as the requesting user, with that user's own key on this config; the
config's default key is never used for a request a user makes.

| Status | Meaning |
|--------|---------|
| `202 Accepted` | The job is queued. The body is the NetBox core Job, as `/api/core/jobs/{id}/` returns it. |
| `403 Forbidden` | The requesting user has no API key on this config (`{"detail": "No API key configured for this RIR config."}`), or lacks the NetBox permission below. |
| `404 Not Found` | No config with that id is visible to the user. |

Like the other plugin actions, the request is a `POST`, so NetBox requires the
`add` permission on RIR configs (`netbox_rir_manager.add_rirconfig`), and a token
with write access.

Poll the returned job until its `status` is `completed`, `failed` or `errored`:

```bash
JOB_URL=$(curl -s -X POST \
  -H "Authorization: Token $TOKEN" -H "Accept: application/json" \
  https://netbox.example.com/api/plugins/rir-manager/configs/1/sync/ | jq -r .url)
curl -s -H "Authorization: Token $TOKEN" -H "Accept: application/json" "$JOB_URL" | jq .status.value
```

```json
{
  "id": 7058,
  "url": "https://netbox.example.com/api/core/jobs/7058/",
  "object_type": "netbox_rir_manager.rirconfig",
  "object_id": 1,
  "name": "RIR Sync",
  "status": {"value": "pending", "label": "Pending"},
  "created": "2026-11-03T10:00:00-05:00",
  "user": {"id": 3, "username": "automation"},
  "data": null,
  "job_id": "5f0c..."
}
```

The job's `data` gains `sync_logs_count` when it finishes; the per-object results
are in `/api/plugins/rir-manager/sync-logs/`. The per-aggregate prefix discovery
runs as separate `ARIN Prefix Sync` jobs, which the sync job queues as it ends.

## Authentication

Use NetBox token auth -- see the [NetBox REST API docs](https://netboxlabs.com/docs/netbox/en/stable/integrations/rest-api/).
