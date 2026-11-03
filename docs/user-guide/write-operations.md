# Write Operations

From a **Network** detail view, you can act against the RIR directly:

| Operation     | Effect                                                                 |
|---------------|------------------------------------------------------------------------|
| **Reassign**  | Reassign a subnet from a parent network                                |
| **Reallocate**| Reallocate a subnet from a parent network                              |
| **Remove**    | Remove a previously reassigned/reallocated network                     |
| **Delete**    | Submit a deletion request to the RIR                                   |

Operations that require RIR-side approval create a ticket. Tickets are visible under **RIR Manager -> Tickets** and update as the RIR transitions them through their states.

## Reassigning a prefix

A Prefix detail page has a **Reassign** button for prefixes under an aggregate linked to an RIR network. The form is pre-filled from the prefix:

- **Type**: detailed, with the org handle, when the prefix's tenant is linked to an RIR Organization; simple otherwise.
- **Customer**: the tenant's name and the site's address (for a simple reassignment).
- **Net name**: generated from the tenant and the prefix (see [Network names](#network-names)).

Edit anything before submitting: the reassignment is sent to the RIR immediately with exactly the values in the form, using your own key. It does not require **Auto reassign** on the parent; that flag only controls the automatic path below. The new child network is linked to the prefix, and the ticket opens on success.

## Automatic reassignment and removal

Both are opt-in per parent allocation: set **Auto reassign** on the `RIRNetwork` linked to the aggregate. The flag only takes effect while that network's RIR config is active.

- **Reassignment**: when an active prefix under the allocation is saved with a Site scope and a Tenant, and has no linked RIR network yet, a reassign job is queued.
- **Removal**: when a prefix with a linked child reassignment is deleted, or saved with any status other than Active, a job is queued to remove that reassignment at the RIR.

Both run with the key of the user who edited the prefix; see [Which key an operation uses](user-api-keys.md#which-key-an-operation-uses).

Without the opt-in, deleting or deactivating a prefix never touches the RIR: the network is left in place and a `skipped` sync log row (operation `remove`) records the prefix change. Parent allocations themselves (networks linked to an aggregate) are never removed automatically.

## Network names

ARIN accepts net names of up to 50 ASCII letters, numbers, hyphens and spaces. The Reassign and Reallocate forms and API actions reject anything else before contacting ARIN.

Names the plugin generates (the automatic reassignment job, and the pre-filled name on a prefix's Reassign form) follow ARIN's own convention: the tenant name and the prefix, uppercased, with accents stripped and every other character turned into a hyphen -- `Adaptiv Networks Inc.` and `50.21.160.32/29` become `ADAPTIV-NETWORKS-INC-50-21-160-32-29`. When that would exceed 50 characters, the tenant part is shortened; the prefix is always kept whole.
