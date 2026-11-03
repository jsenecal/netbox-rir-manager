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

The **RIR Manager** menu shows each item to users holding its `view_*` permission, and the **+** button to users holding `add_*`.

## Actions in the web UI

Each action page requires the same NetBox permission as its REST API counterpart: the `add` permission on the model the action acts on. As in the REST API, the object must fall within that permission's constraints, so a constrained permission limits which objects a user can act on. A user without the permission gets `403 Forbidden`, and an object outside its constraints gives `404 Not Found`. The GET pages that show an action's form or confirmation need the same permission as submitting it.

| Action                                                   | Permission                       | Also requires                         |
|----------------------------------------------------------|----------------------------------|---------------------------------------|
| **Sync** on an RIR config, and **Sync Selected**         | `add_rirconfig` on the config    | The user's own key on the config      |
| **Reassign**, **Reallocate**, **Remove**, **Delete at ARIN** on an RIR network | `add_rirnetwork` on the network | The user's own key on the network's config |
| **Sync** on an Aggregate                                 | `add_rirconfig` on an active config for the aggregate's RIR | `view_aggregate`, and the user's own key on that config |
| **Sync** on a Prefix                                     | `add_rirconfig` on the config that owns the parent network | `view_prefix`, and the user's own key on that config |
| **Reassign** on a Prefix                                 | `add_rirnetwork` on the parent network | `view_prefix`, and the user's own key on the parent network's config |
| **Resolve** on a Site's RIR Address panel, and selecting a candidate | `add_riraddress`; the saved address must fall within its constraints | `view_site` |
| **Refresh** on a ticket                                  | `add_rirticket` on the ticket    | Nothing else                          |

**Sync Selected** syncs only the selected configs the user's `add_rirconfig` permission covers. The aggregate and prefix **Sync** have no REST endpoint of their own; they do for one object what a config's **Sync** does for all of them, so they need the config sync's permission.

Pages show an action's button only to users who can use it: **Sync Now** on a config, the **ARIN Actions** menu on a network, **Refresh Status** on a ticket, **Sync Selected** on the config list, the **Sync from ARIN** and **Reassign at ARIN** buttons on aggregates and prefixes, and **Resolve** on a site. The site panel's edit button needs `change_riraddress` on the address.

The NetBox permission decides who may act; the key still decides what is sent to the RIR. Without a key of their own on the config, nothing is sent (see [Which key an operation uses](../user-guide/user-api-keys.md#which-key-an-operation-uses)).

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

These run from signals when a prefix is saved or deleted, so the NetBox permission that matters is the one on the prefix (`ipam.add_prefix`, `ipam.change_prefix`, `ipam.delete_prefix`): a reassignment can be queued when a prefix is created as well as when it is edited. The queued job runs with the key of the user who edited the prefix; see [Automatic reassignment and removal](../user-guide/write-operations.md#automatic-reassignment-and-removal).

## User keys

A user key's form lets the editor pick any NetBox user, and the list shows every key the viewer's permission allows. To let users manage only their own keys, constrain their `RIRUserKey` permissions to themselves with NetBox's `$user` token:

```json
{"user": "$user"}
```

The API key itself is never displayed: the detail page masks it and the REST API treats it as write-only.
