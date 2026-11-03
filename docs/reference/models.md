# Models

All models live in `netbox_rir_manager/models/` and subclass `NetBoxModel`, so each one also has NetBox's standard `id`, `created`, `last_updated`, `custom_field_data` and `tags`, and appears in the changelog.

```
ipam.RIR <-- RIRConfig <-- RIRUserKey --> User
                 |
                 +-- RIROrganization --> tenancy.Tenant
                 |       ^
                 +-- RIRContact --> tenancy.Contact
                 |
                 +-- RIRNetwork --> ipam.Aggregate / ipam.Prefix
                 |       ^
                 +-- RIRCustomer --> tenancy.Tenant
                 +-- RIRTicket
                 +-- RIRSyncLog

RIRAddress --> dcim.Site / dcim.Location
(used by RIROrganization, RIRContact, RIRCustomer)
```

## RIRConfig

One set of RIR API settings for one organization, and the parent of every other plugin model that holds RIR data. Its fields, and what deleting a config removes, are described in [RIR Configs](../user-guide/rir-configs.md).

## RIRUserKey

A user's RIR API key for one config. See [User API Keys](../user-guide/user-api-keys.md).

| Field        | Notes                                                    |
|--------------|----------------------------------------------------------|
| `user`       | The NetBox user. Unique together with `rir_config`. The key is not used while this user is deactivated. |
| `rir_config` | The config the key belongs to.                           |
| `api_key`    | Encrypted at rest; write-only in the REST API.           |

## RIROrganization

An organization synced from the RIR.

| Field         | Notes                                                                     |
|---------------|---------------------------------------------------------------------------|
| `handle`      | RIR handle, unique.                                                       |
| `name`        | Organization name.                                                        |
| `address`     | `RIRAddress`.                                                             |
| `tenant`      | Optional NetBox Tenant. A prefix whose tenant is linked here gets a detailed reassignment to this org instead of a simple one. |
| `raw_data`    | The record as the backend returned it.                                    |
| `last_synced`, `synced_by` | When, and with which `RIRUserKey`, the row was last synced.  |

## RIRContact

A point of contact (POC) synced from the RIR.

| Field          | Notes                                              |
|----------------|----------------------------------------------------|
| `handle`       | RIR handle, unique.                                |
| `contact_type` | `PERSON` or `ROLE`.                                |
| `first_name`, `last_name`, `company_name`, `email`, `phone` | Contact details. |
| `address`      | `RIRAddress`.                                      |
| `organization` | The `RIROrganization` the POC was synced from.     |
| `contact`      | Optional link to a NetBox `tenancy.Contact`.       |
| `raw_data`, `last_synced`, `synced_by` | As on `RIROrganization`.   |

## RIRNetwork

A network (ARIN NET) registered at the RIR.

| Field           | Notes                                                                  |
|-----------------|------------------------------------------------------------------------|
| `handle`        | RIR handle, unique.                                                    |
| `net_name`      | The network name at the RIR.                                           |
| `net_type`      | The RIR's network type.                                                |
| `organization`  | The owning `RIROrganization`, when it has been synced.                 |
| `aggregate`     | The NetBox Aggregate an allocation anchors.                            |
| `prefix`        | The NetBox Prefix a reassignment or reallocation is linked to.         |
| `auto_reassign` | Opts this allocation into automatic reassignment and removal of child prefixes. See [Write Operations](../user-guide/write-operations.md#automatic-reassignment-and-removal). |
| `raw_data`, `last_synced`, `synced_by` | As on `RIROrganization`.                        |

## RIRCustomer

A customer record at the RIR, the holder of a simple reassignment.

| Field           | Notes                                                       |
|-----------------|-------------------------------------------------------------|
| `handle`        | RIR handle, unique.                                         |
| `customer_name` | Customer name.                                              |
| `address`       | `RIRAddress`.                                               |
| `network`       | For a customer the plugin creates during a simple reassignment, the parent allocation the reassignment was made from. For a customer the prefix sync discovers, the child network reassigned to it; the prefix sync re-links a customer it finds to that child network. Deleting the network deletes the customer. |
| `tenant`        | Optional NetBox Tenant. A tenant linked to a customer cannot be deleted. |
| `raw_data`      | The record as the backend returned it.                      |
| `created_date`  | When the customer was created.                              |

## RIRAddress

A structured postal address. See [Addresses and Geocoding](../user-guide/addresses.md).

| Field            | Notes                                                        |
|------------------|--------------------------------------------------------------|
| `site`           | Optional NetBox Site. A Site has at most one address without a location. |
| `location`       | Optional NetBox Location, which must belong to `site`.       |
| `street_address` | One line per address line.                                   |
| `city`           |                                                              |
| `state_province` | ISO 3166-2 subdivision code, such as `QC` or `NY`.           |
| `postal_code`    |                                                              |
| `country`        | ISO 3166-1 alpha-2 code, such as `CA`.                       |
| `raw_geocode`    | The geocoder's full response.                                |
| `auto_resolved`  | `True` when geocoded, `False` when entered by hand.          |
| `last_resolved`  | When the address was last geocoded.                          |

The five address fields are unique together.

## RIRTicket

A request the RIR opened a ticket for. See [Write Operations](../user-guide/write-operations.md).

| Field           | Notes                                                                 |
|-----------------|-----------------------------------------------------------------------|
| `ticket_number` | RIR ticket number, unique.                                            |
| `ticket_type`   | `IPV4_SIMPLE_REASSIGN`, `IPV4_DETAILED_REASSIGN`, `IPV4_REALLOCATE`, `IPV6_DETAILED_REASSIGN`, `IPV6_REALLOCATE` or `NET_DELETE_REQUEST`. |
| `status`        | `pending_confirmation`, `pending_review`, `assigned`, `in_progress`, `resolved`, `closed` or `approved`. |
| `resolution`    | `accepted`, `denied`, `abandoned`, `processed`, `withdrawn` or `other`; blank by default. |
| `network`       | The `RIRNetwork` the request concerns.                                |
| `submitted_by`  | The `RIRUserKey` that submitted the request.                          |
| `created_date`, `resolved_date` | Ticket dates.                                         |
| `raw_data`      | The ticket as the backend returned it.                                |

## RIRSyncLog

One row per operation the plugin performs against the RIR. Its fields are described in [Sync logs](../user-guide/syncing.md#sync-logs).
