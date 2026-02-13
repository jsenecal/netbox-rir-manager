from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class RIRSiteAddress(NetBoxModel):
    """Cached structured address for a NetBox Site, populated via geocoding or manual entry."""

    site = models.OneToOneField(
        "dcim.Site",
        on_delete=models.CASCADE,
        related_name="rir_address",
    )
    street_address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state_province = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ISO-3166-2 subdivision code (e.g. NY, QC)",
    )
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(
        max_length=2,
        blank=True,
        default="",
        help_text="ISO-3166-1 alpha-2 country code",
    )
    raw_geocode = models.JSONField(default=dict, blank=True, help_text="Full geocoder response for debugging")
    auto_resolved = models.BooleanField(default=False, help_text="True if geocoded, False if manually entered")
    last_resolved = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["site__name"]
        verbose_name = "RIR site address"
        verbose_name_plural = "RIR site addresses"

    def __str__(self):
        return f"{self.site.name} - {self.city}, {self.country}" if self.city else f"{self.site.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirsiteaddress", args=[self.pk])
