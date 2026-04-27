# NetBox RIR Manager

> Manage Regional Internet Registry (RIR) resources directly from within NetBox.

[![PyPI version](https://img.shields.io/pypi/v/netbox-rir-manager.svg)](https://pypi.org/project/netbox-rir-manager/)
[![Python](https://img.shields.io/pypi/pyversions/netbox-rir-manager.svg)](https://pypi.org/project/netbox-rir-manager/)
[![NetBox](https://img.shields.io/badge/NetBox-4.5%2B-success.svg)](https://github.com/netbox-community/netbox)
[![CI](https://github.com/jsenecal/netbox-rir-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/jsenecal/netbox-rir-manager/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jsenecal/netbox-rir-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/jsenecal/netbox-rir-manager)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Features

- **Sync RIR resources** -- import organizations, contacts (POCs), networks, and ASNs from your RIR into NetBox
- **Auto-link to IPAM** -- synced networks are linked to existing NetBox Aggregates, Prefixes, and ASNs
- **Write operations** -- reassign, reallocate, remove, and delete networks directly through the plugin
- **Ticket tracking** -- monitor RIR tickets and their status
- **Per-user API keys** -- encrypted at rest
- **Scheduled sync** -- daily background jobs keep RIR data current
- **Pluggable backend architecture** -- ARIN supported today; PRs welcome for RIPE, APNIC, LACNIC, AFRINIC
- **Full REST API** -- every resource and action exposed under `/api/plugins/rir-manager/`
- **Sync logging** -- full audit trail of every sync operation

## Compatibility

| Plugin version | NetBox version | Python    |
|----------------|----------------|-----------|
| 0.3.x          | 4.5            | 3.12-3.14 |

## Installation

### pip

```bash
pip install netbox-rir-manager
```

### From source

```bash
pip install git+https://github.com/jsenecal/netbox-rir-manager.git
```

## Configuration

In your NetBox `configuration.py`:

```python
PLUGINS = [
    "netbox_rir_manager",
]

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

Then run migrations:

```bash
cd /opt/netbox/netbox
python manage.py migrate
```

> **Warning:** the `encryption_key` (or NetBox's `SECRET_KEY` when empty) is used to encrypt stored API keys. Changing or losing it makes previously encrypted keys unrecoverable.

See [Configuration -> Settings](https://jsenecal.github.io/netbox-rir-manager/getting-started/configuration/) for the full reference.

## Documentation

Full documentation: **[jsenecal.github.io/netbox-rir-manager](https://jsenecal.github.io/netbox-rir-manager/)**

- [Installation](https://jsenecal.github.io/netbox-rir-manager/getting-started/installation/)
- [Configuration](https://jsenecal.github.io/netbox-rir-manager/getting-started/configuration/)
- [User guide](https://jsenecal.github.io/netbox-rir-manager/user-guide/rir-configs/)
- [REST API reference](https://jsenecal.github.io/netbox-rir-manager/reference/rest-api/)
- [Development & dev container](https://jsenecal.github.io/netbox-rir-manager/development/dev-container/)

## Contributing

PRs welcome -- especially for additional RIR backends (RIPE, APNIC, LACNIC, AFRINIC). The plugin uses a pluggable backend architecture; see `netbox_rir_manager/backends/base.py` for the abstract `RIRBackend` class.

Use conventional-commits PR titles (`feat:`, `fix:`, `chore:`, `docs:`, ...) -- release-drafter assembles release notes from them. Run `make setup` after cloning to install dev dependencies and the pre-commit hooks (including the AI-attribution-rejecting `commit-msg` hook).

## License

[Apache License 2.0](LICENSE).
