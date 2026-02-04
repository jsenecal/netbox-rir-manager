from netbox.plugins import PluginTemplateExtension

from netbox_rir_manager.models import RIRNetwork


class RIRAggregateExtension(PluginTemplateExtension):
    """Show RIR network info on Aggregate detail page."""

    models = ["ipam.aggregate"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(aggregate=obj)
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={"rir_networks": rir_networks},
        )


class RIRPrefixExtension(PluginTemplateExtension):
    """Show RIR network info on Prefix detail page."""

    models = ["ipam.prefix"]

    def right_page(self):
        obj = self.context["object"]
        rir_networks = RIRNetwork.objects.filter(prefix=obj)
        return self.render(
            "netbox_rir_manager/inc/rir_network_panel.html",
            extra_context={"rir_networks": rir_networks},
        )


template_extensions = [RIRAggregateExtension, RIRPrefixExtension]
