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


@receiver(post_save, sender="ipam.Prefix")
def auto_reassign_prefix(sender, instance, created=False, raw=False, **kwargs):
    """
    Auto-reassign a Prefix at ARIN when it gets both a Site and Tenant,
    and its parent aggregate has an RIRNetwork with auto_reassign=True.

    Trigger conditions (ALL required):
    1. Prefix is scoped to a Site
    2. Prefix has a Tenant
    3. No existing RIRNetwork linked to this prefix
    4. Parent aggregate has a linked RIRNetwork with auto_reassign=True
    5. At least one RIRUserKey exists for the RIRConfig
    """
    if raw:
        return

    from dcim.models import Site
    from ipam.models import Aggregate

    from netbox_rir_manager.models import RIRNetwork, RIRUserKey

    # 1. Check for site - Prefix.scope is a GenericFK via CachedScopeMixin
    site = getattr(instance, "_site", None)
    if site is None:
        scope = getattr(instance, "scope", None)
        if isinstance(scope, Site):
            site = scope
    if not site:
        return

    # 2. Check for tenant
    if not instance.tenant:
        return

    # 3. Check no existing RIRNetwork for this prefix
    if RIRNetwork.objects.filter(prefix=instance).exists():
        return

    # 4. Find parent aggregate with auto_reassign RIRNetwork
    agg = Aggregate.objects.filter(
        prefix__net_contains_or_equals=instance.prefix
    ).first()
    if not agg:
        return

    parent_network = RIRNetwork.objects.filter(aggregate=agg, auto_reassign=True).first()
    if not parent_network:
        return

    # 5. Find a user key for the RIR config
    user_key = RIRUserKey.objects.filter(rir_config=parent_network.rir_config).first()
    if not user_key:
        logger.warning(
            "Auto-reassign skipped for prefix %s: no API key for config %s",
            instance.prefix,
            parent_network.rir_config.name,
        )
        return

    # Enqueue the reassign job
    from netbox_rir_manager.jobs import ReassignJob

    logger.info(
        "Auto-reassign triggered for prefix %s (tenant=%s, site=%s)",
        instance.prefix,
        instance.tenant.name,
        site.name,
    )

    ReassignJob.enqueue(
        instance=parent_network.rir_config,
        user=user_key.user,
        prefix_id=instance.pk,
        user_key_id=user_key.pk,
    )
