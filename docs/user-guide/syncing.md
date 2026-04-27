# Syncing Resources

The plugin imports organizations, contacts (POCs), networks, and ASNs from your RIR into NetBox.

## Manual sync

Trigger a sync from the **RIR Config** detail view. The page reports progress and surfaces errors as they happen. A complete log entry lands under **RIR Manager -> Sync Logs** when the run finishes.

## Scheduled sync

A background RQ job runs automatically on the cadence set by `sync_interval_hours` (default: 24). The first scheduled run starts after `sync_interval_hours` from plugin initialization; thereafter it repeats on that interval.

## Auto-linking

When `auto_link_networks` is enabled (default), each synced network is matched against existing NetBox **Aggregates** and **Prefixes** and linked when a match is found. ASNs are matched against NetBox `ipam.ASN`.

Synced resources appear under **RIR Manager -> Resources**.
