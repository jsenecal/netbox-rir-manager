# NetBox RIR Manager

[![PyPI version](https://img.shields.io/pypi/v/netbox-rir-manager.svg)](https://pypi.org/project/netbox-rir-manager/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/jsenecal/netbox-rir-manager/blob/main/LICENSE)
[![CI](https://github.com/jsenecal/netbox-rir-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/jsenecal/netbox-rir-manager/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jsenecal/netbox-rir-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/jsenecal/netbox-rir-manager)
[![NetBox](https://img.shields.io/badge/NetBox-4.5%2B-blue.svg)](https://github.com/netbox-community/netbox)

A NetBox plugin for managing Regional Internet Registry (RIR) resources directly from within NetBox.

## Features

- **Sync RIR resources** — Import organizations, contacts (POCs), networks, and ASNs from your RIR into NetBox
- **Auto-link to IPAM** — Automatically link synced networks to existing NetBox Aggregates, Prefixes, and ASNs
- **Write operations** — Reassign, reallocate, remove, and delete networks directly through the plugin
- **Ticket tracking** — Monitor RIR tickets (reassignments, reallocations, deletions) and their status
- **Per-user API keys** — Each user stores their own RIR API key with encryption at rest
- **Scheduled sync** — Daily background jobs keep your RIR data up to date
- **Pluggable backend architecture** — Abstract backend system designed to support multiple RIRs (ARIN supported today; PRs welcome for RIPE, APNIC, etc.)
- **Full REST API** — All resources and actions are available through NetBox's REST API
- **Sync logging** — Full audit trail of every sync operation with status and details

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.12+ |
| NetBox | 4.5+ |
| pyregrws | 0.2.0+ |

## Installation

### 1. Install the plugin

```bash
pip install netbox-rir-manager
```

Or if installing from source:

```bash
pip install git+https://github.com/jsenecal/netbox-rir-manager.git
```

### 2. Enable the plugin

Add the plugin to your NetBox `configuration.py`:

```python
PLUGINS = [
    "netbox_rir_manager",
]
```

### 3. Configure the plugin (optional)

Add any configuration overrides to `PLUGINS_CONFIG` in `configuration.py`:

```python
PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "top_level_menu": True,
        "sync_interval_hours": 24,
        "auto_link_networks": True,
        "enabled_backends": ["ARIN"],
        "encryption_key": "",  # defaults to NetBox SECRET_KEY
        "api_retry_count": 3,
        "api_retry_backoff": 2,
    },
}
```

### 4. Run database migrations

```bash
cd /opt/netbox/netbox
python manage.py migrate
```

### 5. Restart NetBox

Restart both the NetBox WSGI service and the RQ worker. The exact command depends on your deployment method (systemd, Docker Compose, etc.). Refer to the [NetBox documentation](https://netboxlabs.com/docs/netbox/en/stable/) for your specific setup.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `top_level_menu` | `True` | Display RIR Manager as a top-level menu item in the NetBox navigation |
| `sync_interval_hours` | `24` | Interval in hours between scheduled background syncs |
| `auto_link_networks` | `True` | Automatically link synced RIR networks to matching NetBox Aggregates and Prefixes |
| `enabled_backends` | `["ARIN"]` | List of enabled RIR backends |
| `encryption_key` | `""` | Key used to encrypt API keys at rest. Falls back to NetBox's `SECRET_KEY` when empty |
| `api_retry_count` | `3` | Number of retries for failed RIR API calls |
| `api_retry_backoff` | `2` | Exponential backoff multiplier between API retries (in seconds) |

> **Warning:** The `encryption_key` (or NetBox's `SECRET_KEY` if left empty) is used to encrypt stored API keys. Changing or losing this key will make all previously encrypted API keys unrecoverable. Store it securely and back it up alongside your database.

## Usage

### Setting up an RIR Config

1. Navigate to **RIR Manager > Configs** and create a new RIR Config
2. Select the RIR backend (e.g. ARIN) and provide the organization handle for your account

### Adding a User API Key

1. Navigate to **RIR Manager > User Keys** and add a new key
2. Select the RIR Config and enter your ARIN Online API key
3. The key is encrypted at rest using the configured `encryption_key`

### Syncing resources

- **Manual sync:** Trigger a sync from the RIR Config detail view
- **Scheduled sync:** A background job runs automatically based on `sync_interval_hours`

Synced resources (organizations, contacts, networks) appear under **RIR Manager > Resources** and are automatically linked to matching NetBox IPAM objects when `auto_link_networks` is enabled.

### Write operations

From a network's detail view, you can perform write operations against the RIR:

- **Reassign** — Reassign a subnet from a parent network
- **Reallocate** — Reallocate a subnet from a parent network
- **Remove** — Remove a reassigned/reallocated network
- **Delete** — Submit a deletion request to the RIR

Write operations that require RIR approval will create a ticket that can be tracked under **RIR Manager > Tickets**.

## REST API

All models and actions are exposed through NetBox's REST API under `/api/plugins/rir-manager/`. Available endpoints:

- `/api/plugins/rir-manager/configs/` — RIR configurations
- `/api/plugins/rir-manager/user-keys/` — Per-user API keys
- `/api/plugins/rir-manager/organizations/` — RIR organizations
- `/api/plugins/rir-manager/contacts/` — RIR contacts (POCs)
- `/api/plugins/rir-manager/networks/` — RIR networks
- `/api/plugins/rir-manager/sync-logs/` — Sync operation logs
- `/api/plugins/rir-manager/tickets/` — RIR tickets

## Development

### Setup

```bash
git clone https://github.com/jsenecal/netbox-rir-manager.git
cd netbox-rir-manager
pip install -e ".[dev]"
```

### Linting

```bash
ruff check netbox_rir_manager/ tests/
ruff format --check netbox_rir_manager/ tests/
```

### Running tests

```bash
pytest
```

Tests require a running NetBox environment with PostgreSQL and Redis. See the [CI workflow](.github/workflows/ci.yml) for the full setup.

## Contributing

Contributions are welcome! In particular, PRs adding support for additional RIR backends (RIPE, APNIC, LACNIC, AFRINIC) are encouraged. The plugin uses a pluggable backend architecture — see `netbox_rir_manager/backends/base.py` for the abstract `RIRBackend` class to implement.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
