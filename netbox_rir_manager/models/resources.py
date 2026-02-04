from django.db import models
from django.urls import reverse
from ipam.models import Aggregate, Prefix
from netbox.models import NetBoxModel


class RIROrganization(NetBoxModel):
    """Organization record from RIR."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="organizations",
    )
    handle = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    street_address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state_province = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirorganization", args=[self.pk])


class RIRContact(NetBoxModel):
    """Point of Contact record from RIR."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    handle = models.CharField(max_length=50, unique=True)
    contact_type = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    organization = models.ForeignKey(
        RIROrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rircontact", args=[self.pk])


class RIRNetwork(NetBoxModel):
    """Network allocation record from RIR, linked to NetBox Aggregates/Prefixes."""

    account = models.ForeignKey(
        "netbox_rir_manager.RIRAccount",
        on_delete=models.CASCADE,
        related_name="networks",
    )
    handle = models.CharField(max_length=50, unique=True)
    net_name = models.CharField(max_length=100)
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
    raw_data = models.JSONField(default=dict, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return self.handle

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirnetwork", args=[self.pk])
