# Installation

netbox-rir-manager is a standard NetBox plugin and installs the same way any other does. Follow the four steps below from the host that runs your NetBox process and RQ worker.

## Requirements

| Dependency | Version            | Notes                                                |
|------------|--------------------|------------------------------------------------------|
| NetBox     | 4.5+               | The plugin uses NetBox 4.5 generic views and `JobRunner`. |
| Python     | 3.12, 3.13, or 3.14 | Tested in CI against all three.                      |
| pyregrws   | 0.2.0+             | ARIN Reg-RWS client, installed automatically.        |
| geopy      | latest             | Geocoding via Nominatim, installed automatically.    |
| pycountry  | latest             | ISO-3166 subdivision lookups, installed automatically. |
| cryptography | latest           | Fernet encryption for user API keys.                 |
| Redis or Valkey | per NetBox    | Required for the RQ worker that runs sync jobs.      |

## 1. Install the plugin

From PyPI:

```bash
pip install netbox-rir-manager
```

Or directly from a tag or branch:

```bash
pip install git+https://github.com/jsenecal/netbox-rir-manager.git@v0.3.2
```

Use the same Python interpreter that runs NetBox. On a default Debian-style install:

```bash
/opt/netbox/venv/bin/pip install netbox-rir-manager
```

## 2. Enable it in `configuration.py`

Add the plugin module name to NetBox's `PLUGINS` list in `/opt/netbox/netbox/netbox/configuration.py` (or wherever your installation keeps it):

```python
PLUGINS = [
    "netbox_rir_manager",
]
```

You can configure plugin behaviour at the same time. See [Configuration](configuration.md) for the full list of settings:

```python
PLUGINS_CONFIG = {
    "netbox_rir_manager": {
        "enabled_backends": ["ARIN"],
    },
}
```

## 3. Run database migrations

The plugin ships nine models, all under the `netbox_rir_manager` app label. Apply them with NetBox's `manage.py`:

```bash
cd /opt/netbox/netbox
python manage.py migrate netbox_rir_manager
```

You should see `Applying netbox_rir_manager.0001_initial... OK` (and any subsequent migrations). The plugin creates these tables:

- `rirconfig`
- `riruserkey`
- `riraddress`
- `rirorganization`
- `rircontact`
- `rirnetwork`
- `rircustomer`
- `rirsynclog`
- `rirticket`

## 4. Restart NetBox

Restart the WSGI/Gunicorn process and the RQ worker so they pick up the new app and register the system jobs.

For systemd installations:

```bash
sudo systemctl restart netbox netbox-rq
```

For Docker Compose deployments, restart the `netbox` and `netbox-worker` services.

## Verify the install

After restart, confirm the plugin loaded:

1. Sign in to NetBox as a superuser.
2. Look for the **RIR Manager** entry in the navigation. It groups menu items under **Configs**, **Resources**, and **Operations**.
3. Visit `/api/plugins/rir-manager/configs/` to confirm the REST API is registered. An empty `results` list is expected before you create any RIR configs.

You can also check from the shell:

```bash
cd /opt/netbox/netbox
python manage.py shell -c "from netbox_rir_manager import __version__; print(__version__)"
```

## Troubleshooting

- **Plugin not visible in the menu**: confirm the `top_level_menu` setting is `True` (the default), the worker has been restarted, and your user has at least `view_rirconfig` permission.
- **Migrations error referencing `ipam.RIR`**: NetBox 4.5+ is required. Earlier versions do not expose the `RIR` foreign key in the supported form.
- **`encryption_key` warnings on first request**: this is normal until you set a value or accept the default `SECRET_KEY` fallback. See the warning in [Configuration](configuration.md#encryption-and-key-rotation).
- **No background jobs running**: the RQ worker (`netbox-rq`) must be running for sync jobs and the daily `ScheduledRIRSyncJob` to fire.
