from django.db import models
from django.urls import reverse
from django.utils import timezone
from ipam.models import Aggregate, Prefix
from netbox.models import NetBoxModel


class RIROrganization(NetBoxModel):
    """Organization record from RIR."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="organizations",
        verbose_name="RIR config",
    )
    handle = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    address = models.ForeignKey(
        "netbox_rir_manager.RIRAddress",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_organizations",
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_organizations",
        help_text="Link to a NetBox Tenant for automatic detailed reassignment",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    synced_by = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="synced_%(class)ss",
        editable=False,
    )

    class Meta:
        ordering = ["handle"]
        verbose_name = "RIR organization"
        verbose_name_plural = "RIR organizations"

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirorganization", args=[self.pk])


class RIRContact(NetBoxModel):
    """Point of Contact record from RIR."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name="RIR config",
    )
    handle = models.CharField(max_length=50, unique=True)
    contact_type = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.ForeignKey(
        "netbox_rir_manager.RIRAddress",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_contacts",
    )
    organization = models.ForeignKey(
        RIROrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )
    contact = models.ForeignKey(
        "tenancy.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_contacts",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    synced_by = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="synced_%(class)ss",
        editable=False,
    )

    class Meta:
        ordering = ["handle"]
        verbose_name = "RIR contact"
        verbose_name_plural = "RIR contacts"

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rircontact", args=[self.pk])


class RIRNetwork(NetBoxModel):
    """Network allocation record from RIR, linked to NetBox Aggregates/Prefixes."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="networks",
        verbose_name="RIR config",
    )
    handle = models.CharField(max_length=50, unique=True)
    net_name = models.CharField(max_length=100)
    net_type = models.CharField(max_length=50, blank=True, default="")
    organization = models.ForeignKey(
        RIROrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="networks",
    )
    aggregate = models.ForeignKey(
        Aggregate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_networks",
    )
    prefix = models.ForeignKey(
        Prefix,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_networks",
    )
    auto_reassign = models.BooleanField(
        default=False,
        help_text="Automatically reassign child prefixes at ARIN when they get a Site and Tenant",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    synced_by = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="synced_%(class)ss",
        editable=False,
    )

    class Meta:
        ordering = ["handle"]
        verbose_name = "RIR network"
        verbose_name_plural = "RIR networks"

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirnetwork", args=[self.pk])

    @classmethod
    def sync_from_arin(cls, net_data, rir_config, aggregate=None, prefix=None, user_key=None):
        """Create or update an RIRNetwork from ARIN net_data dict.

        Returns (network, created) tuple.
        """
        org = None
        org_handle = net_data.get("org_handle")
        if org_handle:
            org = RIROrganization.objects.filter(handle=org_handle).first()

        defaults = {
            "rir_config": rir_config,
            "net_name": net_data.get("net_name") or "",
            "net_type": net_data.get("net_type") or "",
            "organization": org,
            "raw_data": net_data,
            "last_synced": timezone.now(),
            "synced_by": user_key,
        }
        if aggregate is not None:
            defaults["aggregate"] = aggregate
        if prefix is not None:
            defaults["prefix"] = prefix

        return cls.objects.update_or_create(
            handle=net_data["handle"],
            defaults=defaults,
        )

    @classmethod
    def find_for_prefix(cls, prefix):
        """Find the parent RIRNetwork for a prefix via its containing Aggregate."""
        agg = Aggregate.objects.filter(prefix__net_contains_or_equals=prefix.prefix).first()
        if not agg:
            return None, None
        network = cls.objects.filter(aggregate=agg).first()
        return network, agg

    def enqueue_removal(self):
        """Queue a background job to remove this network at ARIN.

        Returns True if job was enqueued, False if no API key available.
        """
        from netbox_rir_manager.jobs import RemoveNetworkJob
        from netbox_rir_manager.models import RIRUserKey

        user_key = RIRUserKey.objects.filter(rir_config=self.rir_config).first()
        if not user_key:
            return False

        RemoveNetworkJob.enqueue(
            instance=self.rir_config,
            user=user_key.user,
            network_id=self.pk,
            user_key_id=user_key.pk,
        )
        return True
