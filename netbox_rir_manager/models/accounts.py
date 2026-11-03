from django.core.exceptions import ValidationError
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
    default_key = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="default key",
        help_text="Key used for work no user initiated, such as the scheduled sync",
    )
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

    def clean(self):
        super().clean()
        if self.default_key_id and self.default_key.rir_config_id != self.pk:
            raise ValidationError({"default_key": "The default key must belong to this RIR config."})
        if self.default_key_id and not self.default_key.user.is_active:
            raise ValidationError(
                {"default_key": f"The default key belongs to deactivated user {self.default_key.user}; choose another."}
            )

    def resolve_key(self, user=None):
        """Return the key an RIR operation should run with, or None if it must not run.

        An operation a user initiated runs only with that user's own key, so the RIR's audit
        trail names the person who acted. The default key is reserved for work no user
        initiated, such as the scheduled sync.

        A key whose owner is deactivated never resolves, the same as if the owner were deleted.
        """
        if user is not None:
            return self.user_keys.filter(user=user, user__is_active=True).first()
        key = self.default_key
        return key if key is not None and key.user.is_active else None

    def no_key_reason(self, user=None):
        """Explain why resolve_key(user) returned None, for logs and skipped sync log rows."""
        if user is not None:
            if not user.is_active:
                return f"{user} is deactivated, so none of their API keys are used for RIR config {self}"
            return f"{user} has no API key for RIR config {self}"
        if self.default_key is not None:
            return f"The default key for RIR config {self} belongs to deactivated user {self.default_key.user}"
        return f"RIR config {self} has no default key"
