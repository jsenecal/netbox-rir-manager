from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem, get_plugin_config

configs_items = (
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rirconfig_list",
        link_text="RIR Configs",
        permissions=["netbox_rir_manager.view_rirconfig"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:rirconfig_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_rirconfig"],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:riruserkey_list",
        link_text="User Keys",
        permissions=["netbox_rir_manager.view_riruserkey"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:riruserkey_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_riruserkey"],
            ),
        ),
    ),
)

resources_items = (
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rirorganization_list",
        link_text="Organizations",
        permissions=["netbox_rir_manager.view_rirorganization"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:rirorganization_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_rirorganization"],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rircontact_list",
        link_text="Contacts (POCs)",
        permissions=["netbox_rir_manager.view_rircontact"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:rircontact_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_rircontact"],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rirnetwork_list",
        link_text="Networks",
        permissions=["netbox_rir_manager.view_rirnetwork"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:rirnetwork_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_rirnetwork"],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rircustomer_list",
        link_text="Customers",
        permissions=["netbox_rir_manager.view_rircustomer"],
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:riraddress_list",
        link_text="Addresses",
        permissions=["netbox_rir_manager.view_riraddress"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_rir_manager:riraddress_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_rir_manager.add_riraddress"],
            ),
        ),
    ),
)

operations_items = (
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rirsynclog_list",
        link_text="Sync Logs",
        permissions=["netbox_rir_manager.view_rirsynclog"],
    ),
    PluginMenuItem(
        link="plugins:netbox_rir_manager:rirticket_list",
        link_text="Tickets",
        permissions=["netbox_rir_manager.view_rirticket"],
    ),
)

if get_plugin_config("netbox_rir_manager", "top_level_menu", True):
    # Register a top-level "RIR Manager" menu.
    menu = PluginMenu(
        label="RIR Manager",
        groups=(
            ("Configs", configs_items),
            ("Resources", resources_items),
            ("Operations", operations_items),
        ),
        icon_class="mdi mdi-earth",
    )
else:
    # List the items under the plugin's section of the shared Plugins menu.
    menu_items = configs_items + resources_items + operations_items
