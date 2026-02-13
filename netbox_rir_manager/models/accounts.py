from django.db import models
from django.urls import reverse
from ipam.models import RIR
from netbox.models import NetBoxModel
from netbox.models.features import JobsMixin

from netbox_rir_manager.fields import LenientURLField


class RIRConfig(JobsMixin, NetBoxModel):
    """Organization-level configuration for RIR API access."""

    rir = models.ForeignKey(RIR, on_delete=models.CASCADE, related_name="rir_configs", verbose_name="RIR")
    name = models.CharField(max_length=100)
    api_url = LenientURLField(blank=True, default="", verbose_name="API URL")
    org_handle = models.CharField(max_length=50, blank=True, default="", verbose_name="org handle")
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rir", "name"]
        verbose_name = "RIR config"
        verbose_name_plural = "RIR configs"
        constraints = [
            models.UniqueConstraint(fields=["rir", "name"], name="unique_rir_config_name"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirconfig", args=[self.pk])
