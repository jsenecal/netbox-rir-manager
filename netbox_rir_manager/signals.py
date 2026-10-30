import ipaddress
import logging

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
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
    4. Parent aggregate has a linked RIRNetwork with auto_reassign=True on an active config
    5. A key resolves for the user who saved the prefix (see RIRConfig.resolve_key)
    """
    if raw:
        return

    if instance.status != "active":
        return

    from dcim.models import Site

    from netbox_rir_manager.models import RIRNetwork

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

    # 4. Parent allocation opted into auto-reassign on an active config
    parent_network = RIRNetwork.auto_reassign_parent_for(instance)
    if not parent_network:
        return

    # 5. Resolve the key for whoever saved the prefix
    rir_config = parent_network.rir_config
    user = _acting_user()
    user_key = rir_config.resolve_key(user)
    if not user_key:
        reason = _no_key_reason(rir_config, user)
        logger.warning("Auto-reassign skipped for prefix %s: %s", instance.prefix, reason)
        _log_skipped(
            rir_config, "reassign", str(instance.prefix), f"Auto-reassign of {instance.prefix} skipped: {reason}"
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
        instance=rir_config,
        user=user or user_key.user,
        prefix_id=instance.pk,
        user_key_id=user_key.pk,
    )


@receiver(post_save, sender="ipam.Prefix")
def remove_network_on_prefix_deactivate(sender, instance, created=False, raw=False, **kwargs):
    """Remove ARIN reassignment when a prefix is no longer active."""
    if raw or created:
        return

    if instance.status == "active":
        return

    _remove_child_networks(instance, reason="deactivated")


@receiver(pre_delete, sender="ipam.Prefix")
def remove_rir_network_on_prefix_delete(sender, instance, **kwargs):
    """Remove ARIN reassignment when a prefix is deleted.

    Uses pre_delete because after deletion SET_NULL clears the FK link.
    """
    _remove_child_networks(instance, reason="deleted")


def _remove_child_networks(prefix, reason):
    """Queue ARIN removal of a prefix's child reassignments, under the same opt-in as auto-reassign.

    Removal at ARIN is destructive and a prefix status change or delete is a routine IPAM edit,
    so it only happens when the parent allocation has auto_reassign enabled and its config is
    active. Otherwise the ARIN net is left in place and a skipped sync log records why.
    Parent allocations (networks linked to an aggregate) are never removed this way.
    """
    from netbox_rir_manager.models import RIRNetwork

    rir_networks = RIRNetwork.objects.filter(prefix=prefix, aggregate__isnull=True)
    if not rir_networks.exists():
        return

    opted_in = RIRNetwork.auto_reassign_parent_for(prefix) is not None
    user = _acting_user()

    for network in rir_networks:
        if not opted_in:
            _log_skipped(
                network.rir_config,
                "remove",
                network.handle,
                f"Prefix {prefix.prefix} {reason}; ARIN network left in place because its parent "
                "allocation does not have auto-reassign enabled on an active config",
            )
        elif not network.enqueue_removal(user=user):
            no_key = _no_key_reason(network.rir_config, user)
            logger.warning(
                "Cannot remove ARIN network %s for %s prefix %s: %s", network.handle, reason, prefix.prefix, no_key
            )
            _log_skipped(
                network.rir_config,
                "remove",
                network.handle,
                f"Prefix {prefix.prefix} {reason}; ARIN network left in place: {no_key}",
            )


def _acting_user():
    """The authenticated user behind the current request or job, if any."""
    from netbox.context import current_request

    user = getattr(current_request.get(), "user", None)
    return user if user is not None and user.is_authenticated else None


def _no_key_reason(rir_config, user):
    if user is not None:
        return f"{user} has no API key for RIR config {rir_config}"
    return f"RIR config {rir_config} has no default key"


def _log_skipped(rir_config, operation, handle, message):
    from netbox_rir_manager.models import RIRSyncLog

    RIRSyncLog.objects.create(
        rir_config=rir_config,
        operation=operation,
        object_type="network",
        object_handle=handle,
        status="skipped",
        message=message,
    )
