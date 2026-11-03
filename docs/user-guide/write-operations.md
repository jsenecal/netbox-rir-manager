# Write Operations

From a **Network** detail view, you can act against the RIR directly:

| Operation     | Effect                                                                 |
|---------------|------------------------------------------------------------------------|
| **Reassign**  | Reassign a subnet from a parent network                                |
| **Reallocate**| Reallocate a subnet from a parent network                              |
| **Remove**    | Remove a previously reassigned/reallocated network                     |
| **Delete**    | Submit a deletion request to the RIR                                   |

Operations that require RIR-side approval create a ticket. Tickets are visible under **RIR Manager -> Tickets** and update as the RIR transitions them through their states. On success the ticket page opens.

ARIN processes some operations immediately and opens no ticket -- NET deletes and simple reassignments, for example. Those create no ticket: the result is recorded as a `success` sync log under **RIR Manager -> Sync Logs**, any new child network is still linked, and you return to the network (or prefix) page with a message saying ARIN processed the change immediately.

If NetBox cannot record a change ARIN has already accepted, you get a warning that the change succeeded at ARIN but was not recorded, the error is written to the NetBox log and, when possible, to an `error` sync log. Do not resubmit: the change is already in place at ARIN.

### REST API responses

The `reassign`, `reallocate` and `delete-arin` actions on `/api/plugins/rir-manager/networks/<id>/` answer a write ARIN accepted with:

- **A ticket**: `201 Created` and the ticket, as returned by `/api/plugins/rir-manager/tickets/<id>/`.
- **No ticket**: `200 OK` and

    ```json
    {
      "detail": "Reassignment processed immediately by ARIN; no ticket was opened.",
      "recorded": true,
      "ticket": null,
      "net": {"id": 42, "handle": "NET-192-0-2-0-2", "...": "..."}
    }
    ```

    `net` is the child network NetBox linked from a reassignment or reallocation, otherwise `null`. `recorded` is `false` when ARIN made the change but NetBox could not record it; `detail` then says so.

A failure at ARIN returns `502 Bad Gateway` with a `detail` message, as before.

## Reassigning a prefix

A Prefix detail page has a **Reassign** button for prefixes under an aggregate linked to an RIR network. The form is pre-filled from the prefix:

- **Type**: detailed, with the org handle, when the prefix's tenant is linked to an RIR Organization; simple otherwise.
- **Customer**: the tenant's name and the site's address (for a simple reassignment).
- **Net name**: generated from the tenant and the prefix (see [Network names](#network-names)).

Edit anything before submitting: the reassignment is sent to the RIR immediately with exactly the values in the form, using your own key. It does not require **Auto reassign** on the parent; that flag only controls the automatic path below. The new child network is linked to the prefix, and the ticket opens on success (or the prefix page, when ARIN processed it immediately).

## Automatic reassignment and removal

Both are opt-in per parent allocation: set **Auto reassign** on the `RIRNetwork` linked to the aggregate. The flag only takes effect while that network's RIR config is active.

- **Reassignment**: when an active prefix under the allocation is saved with a Site scope and a Tenant, and has no linked RIR network yet, a reassign job is queued.
- **Removal**: when a prefix with a linked child reassignment is deleted, or saved with any status other than Active, a job is queued to remove that reassignment at the RIR.

Both run with the key of the user who edited the prefix; see [Which key an operation uses](user-api-keys.md#which-key-an-operation-uses).

Without the opt-in, deleting or deactivating a prefix never touches the RIR: the network is left in place and a `skipped` sync log row (operation `remove`) records the prefix change. Parent allocations themselves (networks linked to an aggregate) are never removed automatically.

## Network names

ARIN accepts net names of up to 50 ASCII letters, numbers, hyphens and spaces. The Reassign and Reallocate forms and API actions reject anything else before contacting ARIN.

Names the plugin generates (the automatic reassignment job, and the pre-filled name on a prefix's Reassign form) follow ARIN's own convention: the tenant name and the prefix, uppercased, with accents stripped and every other character turned into a hyphen -- `Adaptiv Networks Inc.` and `50.21.160.32/29` become `ADAPTIV-NETWORKS-INC-50-21-160-32-29`. When that would exceed 50 characters, the tenant part is shortened; the prefix is always kept whole.
