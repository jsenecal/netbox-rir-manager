# NetBox RIR Manager

Manage Regional Internet Registry (RIR) resources -- organizations, contacts, networks, customers, addresses, and tickets -- directly from NetBox.

netbox-rir-manager bridges your NetBox IPAM data and the RIR's own database. Synced resources land in dedicated plugin models (`RIROrganization`, `RIRContact`, `RIRNetwork`, etc.) and are auto-linked to their NetBox counterparts (`ipam.Aggregate`, `ipam.Prefix`). Write actions such as reassignment, reallocation, and deletion are submitted to the RIR through a pluggable backend, with every operation persisted in a sync log and (where applicable) a tracked ticket.

## Highlights

- **Sync RIR resources** into NetBox: organizations, points of contact, network allocations, customers.
- **Auto-link to IPAM**: synced networks are matched to existing NetBox `Aggregate` and `Prefix` objects via `auto_link_networks`.
- **Write operations**: reassign, reallocate, remove, and delete networks directly from the plugin or the parent Prefix detail page.
- **Auto-reassign on prefix changes**: when a NetBox `Prefix` gains a Site and Tenant, a background reassignment can be queued automatically.
- **Ticket tracking**: every reassignment, reallocation, and deletion creates an `RIRTicket` whose status follows the RIR.
- **Per-user API keys**: encrypted at rest with HKDF-derived Fernet, scoped to a single `RIRConfig`.
- **Scheduled sync**: a daily system job (`ScheduledRIRSyncJob`) keeps RIR data current.
- **Pluggable backend architecture**: ARIN supported today via `pyregrws`; PRs welcome for RIPE, APNIC, LACNIC, AFRINIC.
- **Address geocoding**: Site addresses are normalised into structured `RIRAddress` records using Nominatim (and optionally Google).
- **Full REST API** under `/api/plugins/rir-manager/` with custom action endpoints for write operations.
- **Sync logging**: full audit trail of every read and write operation under `RIRSyncLog`.

## How it fits together

```
+-------------------+       +---------------------+
| ipam.RIR          | <---- | RIRConfig           |  org-level binding
+-------------------+       +---------------------+
                                     |
                                     | scopes
                                     v
+-------------------+       +---------------------+
| User              | ----> | RIRUserKey          |  per-user encrypted credential
+-------------------+       +---------------------+
                                     |
                                     | drives
                                     v
+--------------+    +-----------------+    +---------------+
| Backend      |    | Sync jobs       | -> | RIRSyncLog    |
| (pyregrws)   | <- | (RQ)            | -> | RIRTicket     |
+--------------+    +-----------------+    +---------------+
                                     |
                                     | populates
                                     v
+--------------------------------------------------------+
| RIROrganization, RIRContact, RIRNetwork, RIRCustomer,  |
| RIRAddress -- linked to ipam.Aggregate / ipam.Prefix   |
+--------------------------------------------------------+
```

## Quick links

- [Installation](getting-started/installation.md)
- [Configuration](getting-started/configuration.md)
- [First Sync](getting-started/first-sync.md)
- [REST API reference](reference/rest-api.md)
- [Settings reference](reference/settings.md)
- [Architecture](development/architecture.md)
- [GitHub repository](https://github.com/jsenecal/netbox-rir-manager)
- [Issue tracker](https://github.com/jsenecal/netbox-rir-manager/issues)

## Compatibility

| Plugin version | NetBox version | Python    |
|----------------|----------------|-----------|
| 0.3.x          | 4.5            | 3.12-3.14 |

## License

Apache License 2.0. See [LICENSE](https://github.com/jsenecal/netbox-rir-manager/blob/main/LICENSE).
