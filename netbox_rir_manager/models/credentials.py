from django.conf import settings
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from netbox_rir_manager.fields import EncryptedCharField


class RIRUserKey(NetBoxModel):
    """Per-user API key for RIR access, scoped to an RIRConfig."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rir_user_keys",
    )
    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="user_keys",
    )
    api_key = EncryptedCharField(max_length=512)

    class Meta:
        ordering = ["user", "rir_config"]
        constraints = [
            models.UniqueConstraint(fields=["user", "rir_config"], name="unique_user_rir_config"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.rir_config.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:riruserkey", args=[self.pk])
