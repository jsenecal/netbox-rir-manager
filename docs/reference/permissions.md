# Permissions

The plugin defines no custom permissions. Each model gets Django's four standard permissions, which NetBox grants through its object permissions (**Admin > Permissions**):

| Model             | Permissions                                                        |
|-------------------|--------------------------------------------------------------------|
| `RIRConfig`       | `netbox_rir_manager.{view,add,change,delete}_rirconfig`            |
| `RIRUserKey`      | `netbox_rir_manager.{view,add,change,delete}_riruserkey`           |
| `RIROrganization` | `netbox_rir_manager.{view,add,change,delete}_rirorganization`      |
| `RIRContact`      | `netbox_rir_manager.{view,add,change,delete}_rircontact`           |
| `RIRNetwork`      | `netbox_rir_manager.{view,add,change,delete}_rirnetwork`           |
| `RIRCustomer`     | `netbox_rir_manager.{view,add,change,delete}_rircustomer`          |
| `RIRAddress`      | `netbox_rir_manager.{view,add,change,delete}_riraddress`           |
| `RIRSyncLog`      | `netbox_rir_manager.{view,add,change,delete}_rirsynclog`           |
| `RIRTicket`       | `netbox_rir_manager.{view,add,change,delete}_rirticket`            |

## Object views

The list, detail, add, edit, import, bulk edit and delete pages are NetBox's generic views, so they enforce the matching permission (and its constraints) as they do for core models. Customers, sync logs and tickets are created by the plugin, not by hand: their pages offer list, detail and delete only.

The **RIR Manager** menu shows each item to users holding its `view_*` permission, and the **+** button to users holding `add_*`. The **Sync Selected** action on the RIR config list is shown to users holding `change_rirconfig`.

## Actions in the web UI

The action pages below only require a logged-in user. They do not check a NetBox permission on the object they act on:

| Action                                                   | Also requires                         |
|----------------------------------------------------------|---------------------------------------|
| **Sync** on an RIR config, and **Sync Selected**         | The user's own key on the config      |
| **Reassign**, **Reallocate**, **Remove**, **Delete** on an RIR network | The user's own key on the network's config |
| **Sync** on an Aggregate                                 | The user's own key on an active config for the aggregate's RIR |
| **Sync** and **Reassign** on a Prefix                    | The user's own key on the config that owns the parent network |
| **Resolve** on a Site's RIR Address panel (geocode and save an address) | Nothing else                  |
| **Refresh** on a ticket                                  | Nothing else                          |

The key is the real gate for anything sent to the RIR: without a key of their own on the config, nothing is sent (see [Which key an operation uses](../user-guide/user-api-keys.md#which-key-an-operation-uses)). Control who can act at the RIR by controlling who has a key.

## REST API

Requests to the REST API go through NetBox's `TokenPermissions`, which maps the HTTP method to a permission on the endpoint's model:

| Method              | Permission  |
|---------------------|-------------|
| `GET`, `HEAD`       | `view_*`    |
| `POST`              | `add_*`     |
| `PUT`, `PATCH`      | `change_*`  |
| `DELETE`            | `delete_*`  |

The plugin's custom actions are `POST` requests, so they need the `add` permission on their model, the object must fall within that permission's constraints, and a token must have write access:

| Endpoint                                              | Permission                      | Also requires                     |
|-------------------------------------------------------|---------------------------------|-----------------------------------|
| `POST /api/plugins/rir-manager/configs/{id}/sync/`     | `add_rirconfig`                 | The user's own key on the config  |
| `POST /api/plugins/rir-manager/networks/{id}/reassign/` | `add_rirnetwork`              | The user's own key on the config  |
| `POST /api/plugins/rir-manager/networks/{id}/reallocate/` | `add_rirnetwork`            | The user's own key on the config  |
| `POST /api/plugins/rir-manager/networks/{id}/remove/`  | `add_rirnetwork`                | The user's own key on the config  |
| `POST /api/plugins/rir-manager/networks/{id}/delete-arin/` | `add_rirnetwork`            | The user's own key on the config  |
| `POST /api/plugins/rir-manager/tickets/{id}/refresh/`  | `add_rirticket`                 | Nothing else                      |

See [REST API](rest-api.md) for request and response details.

## Automatic reassignment and removal

These run from signals when a prefix is saved or deleted, so the NetBox permission that matters is the one on the prefix (`ipam.change_prefix`, `ipam.delete_prefix`). The queued job runs with the key of the user who edited the prefix; see [Automatic reassignment and removal](../user-guide/write-operations.md#automatic-reassignment-and-removal).

## User keys

A user key's form lets the editor pick any NetBox user, and the list shows every key the viewer's permission allows. To let users manage only their own keys, constrain their `RIRUserKey` permissions to themselves with NetBox's `$user` token:

```json
{"user": "$user"}
```

The API key itself is never displayed: the detail page masks it and the REST API treats it as write-only.
