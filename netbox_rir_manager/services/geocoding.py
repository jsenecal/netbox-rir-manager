from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from dcim.models import Site

    from netbox_rir_manager.models import RIRAddress

logger = logging.getLogger(__name__)


@dataclass
class GeocodingResult:
    """Structured geocoding result with ISO-3166 codes."""

    street_address: str
    city: str
    state_province: str  # ISO-3166-2 subdivision code (e.g. "NY", "QC")
    postal_code: str
    country: str  # ISO-3166-1 alpha-2 (e.g. "US", "CA")
    raw: dict

    @property
    def raw_json(self) -> str:
        import json

        return json.dumps(self.raw)


class GeocodingService(ABC):
    """Abstract base class for geocoding providers."""

    @abstractmethod
    def geocode(self, address: str) -> GeocodingResult | None:
        """Forward geocode an address string to structured components."""

    @abstractmethod
    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        """Reverse geocode coordinates to structured address components."""

    @abstractmethod
    def geocode_many(self, address: str, limit: int = 5) -> list[GeocodingResult]:
        """Forward geocode returning multiple candidates."""

    @abstractmethod
    def reverse_geocode_many(self, lat: float, lng: float, limit: int = 5) -> list[GeocodingResult]:
        """Reverse geocode returning multiple candidates."""


class NominatimGeocoder(GeocodingService):
    """Geocoding via OpenStreetMap Nominatim (using geopy)."""

    def __init__(self, user_agent: str = "netbox-rir-manager"):
        self._user_agent = user_agent

    def _get_geocoder(self):
        from geopy.geocoders import Nominatim

        return Nominatim(user_agent=self._user_agent)

    def geocode(self, address: str) -> GeocodingResult | None:
        try:
            geocoder = self._get_geocoder()
            location = geocoder.geocode(address, addressdetails=True, language="en")
            if location is None:
                return None
            return self._parse_location(location)
        except Exception:
            logger.exception("Nominatim forward geocode failed for: %s", address)
            return None

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        try:
            geocoder = self._get_geocoder()
            location = geocoder.reverse((lat, lng), addressdetails=True, language="en")
            if location is None:
                return None
            return self._parse_location(location)
        except Exception:
            logger.exception("Nominatim reverse geocode failed for: %s, %s", lat, lng)
            return None

    def geocode_many(self, address: str, limit: int = 5) -> list[GeocodingResult]:
        try:
            geocoder = self._get_geocoder()
            locations = geocoder.geocode(address, addressdetails=True, language="en", exactly_one=False, limit=limit)
            if not locations:
                return []
            return [self._parse_location(loc) for loc in locations]
        except Exception:
            logger.exception("Nominatim forward geocode_many failed for: %s", address)
            return []

    def reverse_geocode_many(self, lat: float, lng: float, limit: int = 5) -> list[GeocodingResult]:
        try:
            geocoder = self._get_geocoder()
            # Nominatim reverse geocode doesn't support multiple results natively,
            # so we get one result and return it as a list
            location = geocoder.reverse((lat, lng), addressdetails=True, language="en")
            if location is None:
                return []
            return [self._parse_location(location)]
        except Exception:
            logger.exception("Nominatim reverse geocode_many failed for: %s, %s", lat, lng)
            return []

    def _parse_location(self, location) -> GeocodingResult:
        raw = location.raw or {}
        addr = raw.get("address", {})

        country_code = (addr.get("country_code") or "").upper()
        state = addr.get("state") or addr.get("province") or ""
        state_code = self._resolve_state_code(country_code, state)

        street_parts = []
        if addr.get("house_number"):
            street_parts.append(addr["house_number"])
        if addr.get("road"):
            street_parts.append(addr["road"])

        return GeocodingResult(
            street_address=" ".join(street_parts),
            city=addr.get("city") or addr.get("town") or addr.get("village") or "",
            state_province=state_code,
            postal_code=addr.get("postcode") or "",
            country=country_code,
            raw=raw,
        )

    @staticmethod
    def _resolve_state_code(country_code: str, state_name: str) -> str:
        """Map a state/province name to its ISO-3166-2 subdivision code."""
        if not state_name or not country_code:
            return state_name

        try:
            import pycountry

            # Search for subdivision by name within the country
            subdivisions = pycountry.subdivisions.get(country_code=country_code)
            if not subdivisions:
                return state_name

            state_lower = state_name.lower()
            for sub in subdivisions:
                if sub.name.lower() == state_lower:
                    # Return just the subdivision part (e.g. "US-NY" -> "NY")
                    return sub.code.split("-", 1)[-1]

            return state_name
        except Exception:
            logger.debug("pycountry lookup failed for %s/%s", country_code, state_name)
            return state_name


def _get_geocoding_service() -> GeocodingService:
    """Get the configured geocoding service."""
    from django.conf import settings

    plugin_config = settings.PLUGINS_CONFIG.get("netbox_rir_manager", {})
    provider = plugin_config.get("geocoding_provider", "nominatim")

    if provider == "nominatim":
        return NominatimGeocoder()

    # Default fallback
    return NominatimGeocoder()


def resolve_site_address_candidates(site: Site, query: str | None = None, limit: int = 5) -> list[GeocodingResult]:
    """
    Return multiple geocoding candidates for a Site.

    If query is provided, forward geocode that query.
    Otherwise try reverse geocode from coords, fallback to forward geocode from physical_address.
    Returns empty list if nothing works.
    """
    geocoder = _get_geocoding_service()

    if query:
        return geocoder.geocode_many(query, limit=limit)

    # Try reverse geocode from coordinates
    if site.latitude and site.longitude:
        results = geocoder.reverse_geocode_many(float(site.latitude), float(site.longitude), limit=limit)
        if results:
            return results

    # Fallback to forward geocode from physical address
    if site.physical_address:
        return geocoder.geocode_many(site.physical_address, limit=limit)

    return []


def resolve_site_address(site: Site) -> RIRAddress | None:
    """
    Resolve or return cached structured address for a Site.

    1. If RIRAddress already exists for this Site, return it.
    2. If Site has latitude/longitude, reverse geocode.
    3. Else if Site has physical_address, forward geocode.
    4. If geocoding succeeds, create and return RIRAddress.
    5. If fails, return None.
    """
    from netbox_rir_manager.models import RIRAddress

    # Check for existing cached address
    try:
        return site.rir_address
    except RIRAddress.DoesNotExist:
        pass

    geocoder = _get_geocoding_service()
    result = None

    # Try reverse geocode from coordinates
    if site.latitude and site.longitude:
        result = geocoder.reverse_geocode(float(site.latitude), float(site.longitude))

    # Try forward geocode from physical address
    if result is None and site.physical_address:
        result = geocoder.geocode(site.physical_address)

    if result is None:
        logger.warning("Could not resolve address for site %s (pk=%s)", site.name, site.pk)
        return None

    address = RIRAddress.objects.create(
        site=site,
        street_address=result.street_address,
        city=result.city,
        state_province=result.state_province,
        postal_code=result.postal_code,
        country=result.country,
        raw_geocode=result.raw,
        auto_resolved=True,
        last_resolved=timezone.now(),
    )
    logger.info("Resolved address for site %s: %s, %s", site.name, result.city, result.country)
    return address
