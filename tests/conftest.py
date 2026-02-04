import sys
from types import ModuleType
from unittest.mock import MagicMock

# Mock the netbox module hierarchy so that imports of
# netbox_rir_manager work without a full NetBox installation.
if "netbox" not in sys.modules:
    netbox = ModuleType("netbox")
    netbox.plugins = ModuleType("netbox.plugins")
    netbox.plugins.PluginConfig = type("PluginConfig", (), {})
    sys.modules["netbox"] = netbox
    sys.modules["netbox.plugins"] = netbox.plugins
