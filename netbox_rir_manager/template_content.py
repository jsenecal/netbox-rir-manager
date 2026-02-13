from netbox.plugins import PluginTemplateExtension

from netbox_rir_manager.models import RIRNetwork, RIRSiteAddress


class RIRAggregateExtension(PluginTemplateExtension):
    """Show RIR network info with sync button on Aggregate detail page."""

    models = ["ipam.aggregate"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(aggregate=obj)
        from netbox_rir_manager.models import RIRConfig

        has_rir_config = RIRConfig.objects.filter(rir=obj.rir, is_active=True).exists()
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={
                "rir_networks": rir_networks,
                "show_sync_button": has_rir_config,
                "aggregate_pk": obj.pk,
            },
        )


class RIRPrefixExtension(PluginTemplateExtension):
    """Show RIR network info and reassign button on Prefix detail page."""

    models = ["ipam.prefix"]

    def right_page(self):
        obj = self.context["object"]
        from ipam.models import Aggregate
        from netbox_rir_manager.models import RIRConfig

        rir_networks = RIRNetwork.objects.filter(prefix=obj)

        # Determine if sync button should be shown:
        # Parent aggregate must have an active RIR config
        show_sync_button = False
        agg = Aggregate.objects.filter(
            prefix__net_contains_or_equals=obj.prefix
        ).first()
        if agg and RIRConfig.objects.filter(rir=agg.rir, is_active=True).exists():
            show_sync_button = True

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
        # Show reassign button if:
        # - Parent aggregate has a linked RIRNetwork
        # - This prefix doesn't already have a linked RIRNetwork
        from ipam.models import Aggregate

        can_reassign = False
        if not RIRNetwork.objects.filter(prefix=obj).exists():
            agg = Aggregate.objects.filter(
                prefix__net_contains_or_equals=obj.prefix
            ).first()
            if agg and RIRNetwork.objects.filter(aggregate=agg).exists():
                can_reassign = True

        return self.render(
            "netbox_rir_manager/inc/rir_prefix_buttons.html",
            extra_context={"can_reassign": can_reassign},
        )


class RIRSiteExtension(PluginTemplateExtension):
    """Show structured RIR address on Site detail page."""

    models = ["dcim.site"]

    def right_page(self):
        obj = self.context["object"]
        try:
            site_address = obj.rir_address
        except RIRSiteAddress.DoesNotExist:
            site_address = None

        return self.render(
            "netbox_rir_manager/inc/rir_site_address_panel.html",
            extra_context={"site_address": site_address},
        )


template_extensions = [RIRAggregateExtension, RIRPrefixExtension, RIRSiteExtension]
