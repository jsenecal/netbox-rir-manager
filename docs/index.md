# NetBox RIR Manager

Manage Regional Internet Registry (RIR) resources -- organizations, contacts, networks, and ASNs -- directly from NetBox.

## Highlights

- **Sync RIR resources** into NetBox: organizations, contacts (POCs), networks, ASNs.
- **Auto-link to IPAM** -- synced networks are matched to existing NetBox Aggregates, Prefixes, and ASNs.
- **Write operations** -- reassign, reallocate, remove, and delete networks directly through the plugin.
- **Ticket tracking** -- monitor RIR tickets (reassignments, reallocations, deletions) and their status.
- **Per-user API keys** -- encrypted at rest.
- **Scheduled sync** -- daily background jobs keep RIR data current.
- **Pluggable backend architecture** -- ARIN supported today; PRs welcome for RIPE, APNIC, LACNIC, AFRINIC.
- **Full REST API** under `/api/plugins/rir-manager/`.

## Quick links

- [Installation](getting-started/installation.md)
- [Configuration](getting-started/configuration.md)
- [GitHub repository](https://github.com/jsenecal/netbox-rir-manager)
- [Issue tracker](https://github.com/jsenecal/netbox-rir-manager/issues)
