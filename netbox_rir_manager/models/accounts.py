from django.db import models
from django.urls import reverse
from ipam.models import RIR
from netbox.models import NetBoxModel


class RIRAccount(NetBoxModel):
    """Credentials and configuration for RIR API access."""

    rir = models.ForeignKey(RIR, on_delete=models.CASCADE, related_name="rir_accounts")
    name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=255)
    api_url = models.URLField(blank=True, default="")
    org_handle = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rir", "name"]
        constraints = [
            models.UniqueConstraint(fields=["rir", "name"], name="unique_rir_account_name"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:riraccount", args=[self.pk])
