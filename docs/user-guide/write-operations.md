# Write Operations

From a **Network** detail view, you can act against the RIR directly:

| Operation     | Effect                                                                 |
|---------------|------------------------------------------------------------------------|
| **Reassign**  | Reassign a subnet from a parent network                                |
| **Reallocate**| Reallocate a subnet from a parent network                              |
| **Remove**    | Remove a previously reassigned/reallocated network                     |
| **Delete**    | Submit a deletion request to the RIR                                   |

Operations that require RIR-side approval create a ticket. Tickets are visible under **RIR Manager → Tickets** and update as the RIR transitions them through their states.
