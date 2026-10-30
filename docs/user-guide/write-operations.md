# Write Operations

From a **Network** detail view, you can act against the RIR directly:

| Operation     | Effect                                                                 |
|---------------|------------------------------------------------------------------------|
| **Reassign**  | Reassign a subnet from a parent network                                |
| **Reallocate**| Reallocate a subnet from a parent network                              |
| **Remove**    | Remove a previously reassigned/reallocated network                     |
| **Delete**    | Submit a deletion request to the RIR                                   |

Operations that require RIR-side approval create a ticket. Tickets are visible under **RIR Manager -> Tickets** and update as the RIR transitions them through their states.

## Automatic reassignment and removal

Both are opt-in per parent allocation: set **Auto reassign** on the `RIRNetwork` linked to the aggregate. The flag only takes effect while that network's RIR config is active.

- **Reassignment**: when an active prefix under the allocation is saved with a Site scope and a Tenant, and has no linked RIR network yet, a reassign job is queued.
- **Removal**: when a prefix with a linked child reassignment is deleted, or saved with any status other than Active, a job is queued to remove that reassignment at the RIR.

Both run with the key of the user who edited the prefix; see [Which key an operation uses](user-api-keys.md#which-key-an-operation-uses).

Without the opt-in, deleting or deactivating a prefix never touches the RIR: the network is left in place and a `skipped` sync log row (operation `remove`) records the prefix change. Parent allocations themselves (networks linked to an aggregate) are never removed automatically.
