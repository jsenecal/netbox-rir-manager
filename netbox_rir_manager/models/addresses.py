from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class RIRAddress(NetBoxModel):
    """Structured address for RIR records, optionally linked to a NetBox Site and/or Location."""

    site = models.ForeignKey(
        "dcim.Site",
        on_delete=models.CASCADE,
        related_name="rir_addresses",
        null=True,
        blank=True,
    )
    location = models.OneToOneField(
        "dcim.Location",
        on_delete=models.SET_NULL,
        related_name="rir_address",
        null=True,
        blank=True,
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
        ordering = ["city", "country"]
        verbose_name = "RIR address"
        verbose_name_plural = "RIR addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["street_address", "city", "state_province", "postal_code", "country"],
                name="unique_rir_address",
            ),
            models.UniqueConstraint(
                fields=["site"],
                condition=models.Q(location__isnull=True, site__isnull=False),
                name="unique_site_default_address",
            ),
        ]

    @classmethod
    def get_for_site(cls, site):
        """Return the site-level (no location) address, or None."""
        return cls.objects.filter(site=site, location__isnull=True).first()

    def __str__(self):
        street_line = self.street_address.split("\n")[0] if self.street_address else ""
        parts = [p for p in (street_line, self.city, self.state_province, self.country) if p]
        label = ", ".join(parts) if parts else f"Address #{self.pk}"
        if self.site:
            label = f"{self.site.name} — {label}" if parts else self.site.name
        return label

    def clean(self):
        super().clean()
        if self.location and self.site and self.location.site != self.site:
            raise ValidationError({"location": "Location must belong to the selected site."})
        if self.location and not self.site:
            raise ValidationError({"location": "A site must be selected when specifying a location."})

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:riraddress", args=[self.pk])
