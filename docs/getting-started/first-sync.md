# First Sync

This walkthrough takes a freshly installed plugin from zero to a populated NetBox database, using ARIN as the example backend.

## Prerequisites

- NetBox 4.5 with the plugin installed and migrations applied (see [Installation](installation.md)).
- The RQ worker (`netbox-rq`) is running. Without it, sync jobs queue but never execute.
- An ARIN Online account with an Org ID and a personal API key.
- At least one `ipam.RIR` record (NetBox ships with `ARIN`, `RIPE`, `APNIC`, `LACNIC`, `AFRINIC` after a fresh `manage.py loaddata`; otherwise create them under **IPAM > RIRs**).
- One or more `ipam.Aggregate` rows under that RIR, covering the prefixes you want to manage.

## Step 1: Create an RIR Config

Configs bind the plugin to a specific RIR account. Each combination of `(rir, name)` must be unique.

1. Go to **RIR Manager > Configs** and click **Add**.
2. Fill in:
    - **RIR**: the NetBox RIR (typically `ARIN`).
    - **Name**: a short label, e.g. `production-arin`.
    - **API URL**: leave blank to use the ARIN Reg-RWS default. For OT&E, use `https://reg.ote.arin.net/regrws/`.
    - **Org handle**: your ARIN Org ID, e.g. `EXAMPLE-1`.
    - **Is active**: keep checked. The scheduled sync only touches active configs.
3. Save.

The config detail page now shows a **Sync** action and tabs for **Sync Logs**, **Tickets**, and **Jobs**.

## Step 2: Add your API key

Each user has their own encrypted key, scoped to one config. Without a key, sync and write actions are blocked.

1. Go to **RIR Manager > User Keys** and click **Add**.
2. Choose your user (admins can add keys for other users).
3. Choose the RIR Config you just created.
4. Paste the API key. It is stored encrypted; subsequent edits will not display the cleartext.
5. Save.

See [User API Keys](../user-guide/user-api-keys.md) for details on rotation and encryption.

## Step 3: Trigger a manual sync

From the RIR Config detail view, click **Sync**. This enqueues a `SyncRIRConfigJob` for your user. Two things happen:

1. The org and its POCs are pulled and persisted as `RIROrganization` and `RIRContact` rows.
2. For each NetBox `Aggregate` under this RIR, the plugin queries ARIN for the matching `Net` and writes an `RIRNetwork` row, linking it to the aggregate. A child `SyncPrefixesJob` is enqueued per aggregate to discover any reassigned subnets.

Watch progress under **RIR Manager > Sync Logs** or on the **Jobs** tab of the config. Each operation produces a row with status `success`, `error`, or `skipped`.

## Step 4: Browse the synced data

After the job finishes, you should see entries under:

- **Resources > Organizations** -- one row per synced ORG, including its address.
- **Resources > Contacts (POCs)** -- linked to the organization and (optionally) to a NetBox `tenancy.Contact`.
- **Resources > Networks** -- one row per RIR Net, linked to its `Aggregate` or `Prefix`.
- **Resources > Customers** -- only for child Nets reassigned to a customer (simple reassignment).
- **Resources > Addresses** -- de-duplicated structured addresses.

Visiting an `Aggregate` or `Prefix` detail page in NetBox now shows an **RIR Network** panel on the right, plus action buttons to **Sync** and (for prefixes) **Reassign**.

## Step 5 (optional): Schedule recurring syncs

The plugin registers `ScheduledRIRSyncJob` as a NetBox system job at the daily interval. It iterates every active `RIRConfig`, picks the most-recently-used `RIRUserKey`, and runs `sync_rir_config` for each. No additional setup is required: the worker picks it up after restart.

To inspect or trigger it manually, go to **System > Background Jobs** in NetBox and look for `Scheduled RIR Sync`.

## Next steps

- [Syncing Resources](../user-guide/syncing.md) -- how the sync pipeline maps RIR data into NetBox.
- [Write Operations](../user-guide/write-operations.md) -- reassign, reallocate, remove, and delete networks at the RIR.
- [IPAM Integration](../user-guide/ipam-integration.md) -- the buttons and panels added to NetBox `Aggregate`, `Prefix`, and `Site` pages.
- [Auto-Reassignment](../user-guide/auto-reassignment.md) -- the signal-driven workflow that reassigns prefixes automatically when they get a Site and Tenant.
