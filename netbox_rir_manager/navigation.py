from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

menu = PluginMenu(
    label="RIR Manager",
    groups=(
        (
            "Configs",
            (
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
            ),
        ),
        (
            "Resources",
            (
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
            ),
        ),
        (
            "Operations",
            (
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
            ),
        ),
    ),
    icon_class="mdi mdi-earth",
)
