# Installation

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.12+ |
| NetBox | 4.5+ |
| pyregrws | 0.2.0+ |

## 1. Install the plugin

```bash
pip install netbox-rir-manager
```

Or from source:

```bash
pip install git+https://github.com/jsenecal/netbox-rir-manager.git
```

## 2. Enable it

In your NetBox `configuration.py`:

```python
PLUGINS = [
    "netbox_rir_manager",
]
```

## 3. Run migrations

```bash
cd /opt/netbox/netbox
python manage.py migrate
```

## 4. Restart NetBox

Restart the NetBox WSGI service and the RQ worker. The exact command depends on your deployment method (systemd, Docker Compose, etc.) — see the [NetBox documentation](https://netboxlabs.com/docs/netbox/en/stable/).
