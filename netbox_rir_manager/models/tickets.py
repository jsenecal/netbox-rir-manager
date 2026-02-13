from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from netbox_rir_manager.choices import TicketResolutionChoices, TicketStatusChoices, TicketTypeChoices


class RIRTicket(NetBoxModel):
    """Tracks ARIN ticket requests from write operations."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name="RIR config",
    )
    ticket_number = models.CharField(max_length=50, unique=True)
    ticket_type = models.CharField(max_length=50, choices=TicketTypeChoices)
    status = models.CharField(max_length=30, choices=TicketStatusChoices)
    resolution = models.CharField(max_length=30, choices=TicketResolutionChoices, blank=True, default="")
    network = models.ForeignKey(
        "netbox_rir_manager.RIRNetwork",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    submitted_by = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    created_date = models.DateTimeField()
    resolved_date = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_date"]
        verbose_name = "RIR ticket"
        verbose_name_plural = "RIR tickets"

    def __str__(self):
        return f"Ticket {self.ticket_number}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirticket", args=[self.pk])
