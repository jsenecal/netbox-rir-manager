from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from netbox_rir_manager.models import RIRAccount


class RIRBackend(ABC):
    """Abstract base class for RIR API backends."""

    name: str

    @abstractmethod
    def authenticate(self, account: RIRAccount) -> bool:
        """Validate credentials and establish connection."""
        ...

    @abstractmethod
    def get_organization(self, handle: str) -> dict[str, Any] | None:
        """Retrieve organization details by handle."""
        ...

    @abstractmethod
    def get_network(self, handle: str) -> dict[str, Any] | None:
        """Retrieve network/prefix details."""
        ...

    @abstractmethod
    def get_poc(self, handle: str) -> dict[str, Any] | None:
        """Retrieve Point of Contact details."""
        ...

    @abstractmethod
    def get_asn(self, asn: int) -> dict[str, Any] | None:
        """Retrieve ASN details."""
        ...

    @abstractmethod
    def sync_resources(self, account: RIRAccount, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Sync resources from RIR. Returns list of synced resource dicts."""
        ...
