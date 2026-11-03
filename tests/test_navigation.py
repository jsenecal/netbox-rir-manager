from netbox.plugins import PluginMenu, PluginMenuItem


def test_top_level_menu_chooses_between_own_menu_and_plugins_menu(plugin_settings, reload_plugin_module):
    plugin_settings(top_level_menu=True)
    top_level = reload_plugin_module("navigation")
    plugin_settings(top_level_menu=False)
    flat = reload_plugin_module("navigation")

    assert isinstance(top_level.menu, PluginMenu)
    assert top_level.menu.label == "RIR Manager"
    assert [group.label for group in top_level.menu.groups] == ["Configs", "Resources", "Operations"]
    assert not hasattr(top_level, "menu_items")

    assert not hasattr(flat, "menu")
    assert all(isinstance(item, PluginMenuItem) for item in flat.menu_items)
    grouped_links = [item.link for group in top_level.menu.groups for item in group.items]
    assert len(grouped_links) == 9
    assert [item.link for item in flat.menu_items] == grouped_links
