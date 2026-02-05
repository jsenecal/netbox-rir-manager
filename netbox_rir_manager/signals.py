import ipaddress
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="netbox_rir_manager.RIRNetwork")
def auto_link_network(sender, instance, created, raw=False, **kwargs):
    """Auto-link RIRNetwork to matching Aggregate/Prefix based on net_blocks in raw_data."""
    if raw:
        return

    plugin_config = settings.PLUGINS_CONFIG.get("netbox_rir_manager", {})
    if not plugin_config.get("auto_link_networks", True):
        return

    # Don't overwrite existing links
    if instance.aggregate is not None or instance.prefix is not None:
        return

    net_blocks = (instance.raw_data or {}).get("net_blocks", [])
    if not net_blocks:
        return

    from ipam.models import Aggregate, Prefix

    for block in net_blocks:
        start = block.get("start_address")
        cidr = block.get("cidr_length")
        if not start or cidr is None:
            continue

        try:
            network = ipaddress.ip_network(f"{start}/{cidr}", strict=False)
            prefix_str = str(network)
        except ValueError:
            continue

        # Try matching Aggregate first
        agg = Aggregate.objects.filter(prefix=prefix_str).first()
        if agg:
            instance.aggregate = agg
            instance.save(update_fields=["aggregate"])
            return

        # Then try Prefix
        pfx = Prefix.objects.filter(prefix=prefix_str).first()
        if pfx:
            instance.prefix = pfx
            instance.save(update_fields=["prefix"])
            return
