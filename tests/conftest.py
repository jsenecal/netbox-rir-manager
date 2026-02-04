"""
Pytest configuration for netbox_rir_manager tests.
Sets up Django and NetBox environment for testing.
"""

import os
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Determine if we're in a Django-capable environment
# (NetBox on PYTHONPATH or in devcontainer)
_netbox_available = False
netbox_path = os.environ.get("PYTHONPATH", "/opt/netbox/netbox")
if os.path.isdir(netbox_path):
    if netbox_path not in sys.path:
        sys.path.insert(0, netbox_path)
    _netbox_available = True

# Mock regrws if not installed (for backend tests)
if "regrws" not in sys.modules:
    try:
        import regrws  # noqa: F401
    except ImportError:
        regrws_mod = ModuleType("regrws")
        regrws_api = ModuleType("regrws.api")
        regrws_api_core = ModuleType("regrws.api.core")
        regrws_api_core.Api = MagicMock()
        regrws_models = ModuleType("regrws.models")
        regrws_models.Error = type("Error", (), {})
        sys.modules["regrws"] = regrws_mod
        sys.modules["regrws.api"] = regrws_api
        sys.modules["regrws.api.core"] = regrws_api_core
        sys.modules["regrws.models"] = regrws_models

if _netbox_available:
    # Full Django setup for integration tests
    import pytest

    os.environ["DJANGO_SETTINGS_MODULE"] = "netbox.settings"

    is_ci = "GITHUB_ACTIONS" in os.environ

    if not is_ci:
        os.environ.setdefault("NETBOX_CONFIGURATION", "netbox.configuration_testing")

        from netbox import configuration_testing

        configuration_testing.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("DB_NAME", "netbox"),
                "USER": os.environ.get("DB_USER", "netbox"),
                "PASSWORD": os.environ.get("DB_PASSWORD", ""),
                "HOST": os.environ.get("DB_HOST", "postgres"),
                "PORT": os.environ.get("DB_PORT", "5432"),
                "CONN_MAX_AGE": 300,
            }
        }

        configuration_testing.REDIS = {
            "tasks": {
                "HOST": os.environ.get("REDIS_HOST", "redis"),
                "PORT": int(os.environ.get("REDIS_PORT", 6379)),
                "PASSWORD": os.environ.get("REDIS_PASSWORD", ""),
                "DATABASE": int(os.environ.get("REDIS_DATABASE", 0)),
                "SSL": os.environ.get("REDIS_SSL", "False").lower() == "true",
            },
            "caching": {
                "HOST": os.environ.get("REDIS_CACHE_HOST", os.environ.get("REDIS_HOST", "redis")),
                "PORT": int(os.environ.get("REDIS_CACHE_PORT", os.environ.get("REDIS_PORT", 6379))),
                "PASSWORD": os.environ.get(
                    "REDIS_CACHE_PASSWORD", os.environ.get("REDIS_PASSWORD", "")
                ),
                "DATABASE": int(os.environ.get("REDIS_CACHE_DATABASE", 1)),
                "SSL": os.environ.get(
                    "REDIS_CACHE_SSL", os.environ.get("REDIS_SSL", "False")
                ).lower()
                == "true",
            },
        }

        if not hasattr(configuration_testing, "PLUGINS"):
            configuration_testing.PLUGINS = []
        if "netbox_rir_manager" not in configuration_testing.PLUGINS:
            configuration_testing.PLUGINS.append("netbox_rir_manager")

        if not hasattr(configuration_testing, "PLUGINS_CONFIG"):
            configuration_testing.PLUGINS_CONFIG = {}
        if "netbox_rir_manager" not in configuration_testing.PLUGINS_CONFIG:
            configuration_testing.PLUGINS_CONFIG["netbox_rir_manager"] = {}

    import django

    django.setup()

    @pytest.fixture
    def rir(db):
        """Create a test RIR (ARIN)."""
        from ipam.models import RIR

        return RIR.objects.create(name="ARIN", slug="arin", is_private=False)

    @pytest.fixture
    def rir_account(db, rir):
        """Create a test RIR account."""
        from netbox_rir_manager.models import RIRAccount

        return RIRAccount.objects.create(
            rir=rir,
            name="Test ARIN Account",
            api_key="test-api-key-12345",
            org_handle="TESTORG-ARIN",
            is_active=True,
        )

    @pytest.fixture
    def admin_client(db):
        """Create an admin user and return a Django test client."""
        from django.contrib.auth.models import User
        from django.test import Client

        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        client = Client()
        client.force_login(user)
        return client

else:
    # Mock netbox for pure-Python tests (no Django needed)
    if "netbox" not in sys.modules:
        netbox = ModuleType("netbox")
        netbox_plugins = ModuleType("netbox.plugins")
        netbox_plugins.PluginConfig = type("PluginConfig", (), {})
        sys.modules["netbox"] = netbox
        sys.modules["netbox.plugins"] = netbox_plugins
