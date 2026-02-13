from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel


class RIRCustomer(NetBoxModel):
    """Customer record created at ARIN during simple reassignment."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="customers",
        verbose_name="RIR config",
    )
    handle = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=255)
    address = models.ForeignKey(
        "netbox_rir_manager.RIRAddress",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rir_customers",
    )
    network = models.ForeignKey(
        "netbox_rir_manager.RIRNetwork",
        on_delete=models.CASCADE,
        related_name="customers",
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rir_customers",
    )
    raw_data = models.JSONField(default=dict, blank=True)
    created_date = models.DateTimeField()

    class Meta:
        ordering = ["-created_date"]
        verbose_name = "RIR customer"
        verbose_name_plural = "RIR customers"

    def __str__(self):
        return f"{self.customer_name} ({self.handle})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rircustomer", args=[self.pk])
