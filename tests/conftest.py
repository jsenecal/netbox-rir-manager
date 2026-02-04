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

# Mock the regrws module hierarchy so that tests run without
# pyregrws being installed in the test environment.
if "regrws" not in sys.modules:
    regrws = ModuleType("regrws")
    regrws_api = ModuleType("regrws.api")
    regrws_api_core = ModuleType("regrws.api.core")
    regrws_api_core.Api = MagicMock()
    regrws_models = ModuleType("regrws.models")
    regrws_models.Error = type("Error", (), {})
    sys.modules["regrws"] = regrws
    sys.modules["regrws.api"] = regrws_api
    sys.modules["regrws.api.core"] = regrws_api_core
    sys.modules["regrws.models"] = regrws_models
