from netbox.plugins import PluginConfig

__version__ = "0.1.0"


class NetBoxRIRManagerConfig(PluginConfig):
    name = "netbox_rir_manager"
    verbose_name = "NetBox RIR Manager"
    description = "Manage RIR (ARIN, RIPE, etc.) resources directly from NetBox"
    version = __version__
    author = "Jonathan Senecal"
    author_email = "jonathan@jonathansenecal.com"
    base_url = "rir-manager"
    min_version = "4.5.0"
    required_settings = []
    default_settings = {
        "top_level_menu": True,
        "sync_interval_hours": 24,
        "auto_link_networks": True,
        "enabled_backends": ["ARIN"],
    }


config = NetBoxRIRManagerConfig
