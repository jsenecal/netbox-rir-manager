from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from netbox_rir_manager.choices import SyncOperationChoices, SyncStatusChoices


class RIRSyncLog(NetBoxModel):
    """Audit log for sync operations."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name="RIR config",
    )
    operation = models.CharField(max_length=50, choices=SyncOperationChoices)
    object_type = models.CharField(max_length=50)
    object_handle = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=SyncStatusChoices)
    message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created"]
        verbose_name = "RIR sync log"
        verbose_name_plural = "RIR sync logs"

    def __str__(self):
        return f"{self.operation} {self.object_handle} ({self.status})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirsynclog", args=[self.pk])
