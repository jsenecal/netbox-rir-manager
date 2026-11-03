import importlib
import sys

import pytest
from netbox.plugins import PluginMenu, PluginMenuItem

EXPECTED_LINKS = [
    "plugins:netbox_rir_manager:rirconfig_list",
    "plugins:netbox_rir_manager:riruserkey_list",
    "plugins:netbox_rir_manager:rirorganization_list",
    "plugins:netbox_rir_manager:rircontact_list",
    "plugins:netbox_rir_manager:rirnetwork_list",
    "plugins:netbox_rir_manager:rircustomer_list",
    "plugins:netbox_rir_manager:riraddress_list",
    "plugins:netbox_rir_manager:rirsynclog_list",
    "plugins:netbox_rir_manager:rirticket_list",
]


@pytest.fixture
def load_navigation(monkeypatch, settings):
    """Import navigation.py afresh with the given top_level_menu value."""
    import netbox_rir_manager
    import netbox_rir_manager.navigation  # noqa: F401 -- loaded first so monkeypatch can restore it

    def _load(top_level_menu):
        settings.PLUGINS_CONFIG = {"netbox_rir_manager": {"top_level_menu": top_level_menu}}
        monkeypatch.delitem(sys.modules, "netbox_rir_manager.navigation")
        monkeypatch.delattr(netbox_rir_manager, "navigation")
        return importlib.import_module("netbox_rir_manager.navigation")

    return _load


def test_top_level_menu_true_registers_own_menu(load_navigation):
    navigation = load_navigation(True)

    assert isinstance(navigation.menu, PluginMenu)
    assert navigation.menu.label == "RIR Manager"
    assert [group.label for group in navigation.menu.groups] == ["Configs", "Resources", "Operations"]
    links = [item.link for group in navigation.menu.groups for item in group.items]
    assert links == EXPECTED_LINKS
    assert not hasattr(navigation, "menu_items")


def test_top_level_menu_false_lists_items_under_plugins_menu(load_navigation):
    navigation = load_navigation(False)

    assert not hasattr(navigation, "menu")
    assert all(isinstance(item, PluginMenuItem) for item in navigation.menu_items)
    assert [item.link for item in navigation.menu_items] == EXPECTED_LINKS
