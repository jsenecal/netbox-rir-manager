from netbox.plugins import PluginTemplateExtension

from netbox_rir_manager.models import RIRAddress, RIRConfig, RIRNetwork


def _user(context):
    return context["request"].user


class RIRAggregateExtension(PluginTemplateExtension):
    """Show RIR network info with sync button on Aggregate detail page."""

    models = ["ipam.aggregate"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(aggregate=obj)

        # The Sync view tries the active configs for this RIR that the user may sync (add_rirconfig).
        can_sync = RIRConfig.objects.restrict(_user(self.context), "add").filter(rir=obj.rir, is_active=True).exists()
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={
                "rir_networks": rir_networks,
                "show_sync_button": can_sync,
                "aggregate_pk": obj.pk,
            },
        )


class RIRPrefixExtension(PluginTemplateExtension):
    """Show RIR network info and reassign button on Prefix detail page."""

    models = ["ipam.prefix"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(prefix=obj)

        # The Sync view uses the active config that owns the parent network, and needs
        # add_rirconfig on it.
        parent_network, _agg = RIRNetwork.find_for_prefix(obj)
        show_sync_button = bool(
            parent_network
            and parent_network.rir_config.is_active
            and _user(self.context).has_perm("netbox_rir_manager.add_rirconfig", parent_network.rir_config)
        )

        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={
                "rir_networks": rir_networks,
                "show_sync_button": show_sync_button,
                "prefix_pk": obj.pk,
            },
        )

    def buttons(self):
        obj = self.context["object"]
        # Offer Reassign when the prefix has no RIRNetwork of its own yet, and the user may
        # reassign from the parent network (add_rirnetwork), as the Reassign view requires.
        can_reassign = False
        if not RIRNetwork.objects.filter(prefix=obj).exists():
            parent_network, _agg = RIRNetwork.find_for_prefix(obj)
            can_reassign = bool(
                parent_network and _user(self.context).has_perm("netbox_rir_manager.add_rirnetwork", parent_network)
            )

        return self.render(
            "netbox_rir_manager/inc/rir_prefix_buttons.html",
            extra_context={"can_reassign": can_reassign},
        )


class RIRSiteExtension(PluginTemplateExtension):
    """Show structured RIR address on Site detail page."""

    models = ["dcim.site"]

    def right_page(self):
        obj = self.context["object"]
        user = _user(self.context)
        site_address = RIRAddress.get_for_site(obj)

        return self.render(
            "netbox_rir_manager/inc/rir_site_address_panel.html",
            extra_context={
                "site_address": site_address,
                "can_resolve": user.has_perm("netbox_rir_manager.add_riraddress"),
                "can_edit_address": bool(site_address)
                and user.has_perm("netbox_rir_manager.change_riraddress", site_address),
            },
        )


template_extensions = [RIRAggregateExtension, RIRPrefixExtension, RIRSiteExtension]
