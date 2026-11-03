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

# Nominatim addressdetails keys holding the full ISO 3166-2 code ("DE-NW"), in order of preference.
# lvl4 is the state/province level that the "state" name describes.
NOMINATIM_ISO_KEYS = ("ISO3166-2-lvl4", "ISO3166-2-lvl6")


def subdivision_code_error(state_name: str) -> str:
    """The user-facing message for a geocoded state/province with no known ISO 3166-2 code."""
    return (
        f"Could not determine the ISO 3166-2 subdivision code for '{state_name}'; enter it on the Site's RIR address."
    )


class SubdivisionCodeError(ValueError):
    """Geocoding found a state/province but not its ISO 3166-2 code, so the address cannot be saved."""


@dataclass
class GeocodingResult:
    """Structured geocoding result with ISO-3166 codes."""

    street_address: str
    city: str
    state_province: str  # ISO-3166-2 subdivision code (e.g. "NY", "QC"), empty when unknown
    postal_code: str
    country: str  # ISO-3166-1 alpha-2 (e.g. "US", "CA")
    raw: dict
    state_name: str = ""  # The state/province name as the geocoder returned it

    @property
    def subdivision_error(self) -> str:
        """Why this result cannot be saved as an address, or "" when it can."""
        if self.state_name and not self.state_province:
            return subdivision_code_error(self.state_name)
        return ""

    @property
    def display_name(self) -> str:
        return self.raw.get("display_name", "")

    @property
    def address_key(self) -> tuple:
        """Key for deduplication based on structured address fields."""
        return (self.street_address, self.city, self.state_province, self.postal_code, self.country)

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

        street_parts = []
        if addr.get("house_number"):
            street_parts.append(addr["house_number"])
        if addr.get("road"):
            street_parts.append(addr["road"])

        return GeocodingResult(
            street_address=" ".join(street_parts),
            city=addr.get("city") or addr.get("town") or addr.get("village") or "",
            state_province=self._resolve_state_code(country_code, state, addr),
            postal_code=addr.get("postcode") or "",
            country=country_code,
            raw=raw,
            state_name=state,
        )

    @classmethod
    def _resolve_state_code(cls, country_code: str, state_name: str, addr: dict) -> str:
        """Find the ISO 3166-2 subdivision code, without its country prefix ("NW" for "DE-NW").

        Nominatim's own lvl4 code is preferred. Otherwise the state name is looked up in
        pycountry, then Nominatim's lvl6 code is tried. Returns "" when no code is found:
        the name itself is never returned, since it is not a code and may not fit the field.
        """
        if not country_code:
            return ""
        lvl4, lvl6 = (cls._nominatim_code(country_code, addr.get(key)) for key in NOMINATIM_ISO_KEYS)
        return lvl4 or cls._pycountry_code(country_code, state_name) or lvl6

    @staticmethod
    def _nominatim_code(country_code: str, code) -> str:
        """The subdivision part of a Nominatim ISO 3166-2 code, if it belongs to country_code."""
        prefix = f"{country_code}-"
        if isinstance(code, str) and code.upper().startswith(prefix):
            return code[len(prefix) :].upper()
        return ""

    @staticmethod
    def _pycountry_code(country_code: str, state_name: str) -> str:
        """Match a state name against pycountry's subdivision names and their English translations.

        pycountry's names are in the local language ("Nordrhein-Westfalen") while Nominatim is
        asked for English names, so the English translation is compared too where one exists.
        """
        if not state_name:
            return ""

        import gettext

        import pycountry

        english = gettext.translation("iso3166-2", pycountry.LOCALES_DIR, languages=["en"], fallback=True)
        wanted = state_name.casefold()
        for sub in pycountry.subdivisions.get(country_code=country_code) or ():
            if wanted in (sub.name.casefold(), english.gettext(sub.name).casefold()):
                return sub.code.split("-", 1)[-1]
        return ""


def _get_geocoding_service() -> GeocodingService:
    """Get the configured geocoding service."""
    from netbox.plugins import get_plugin_config

    provider = get_plugin_config("netbox_rir_manager", "geocoding_provider")

    if provider == "nominatim":
        return NominatimGeocoder()

    # Default fallback
    return NominatimGeocoder()


def _deduplicate_results(results: list[GeocodingResult]) -> list[GeocodingResult]:
    """Remove candidates with identical structured address fields, keeping the first."""
    seen: set[tuple] = set()
    unique = []
    for r in results:
        if r.address_key not in seen:
            seen.add(r.address_key)
            unique.append(r)
    return unique


def resolve_site_address_candidates(site: Site, query: str | None = None, limit: int = 5) -> list[GeocodingResult]:
    """
    Return multiple geocoding candidates for a Site.

    If query is provided, forward geocode that query (with fallback to site data if empty).
    Otherwise try reverse geocode from coords, fallback to forward geocode from physical_address.
    Returns empty list if nothing works. Duplicates are removed.
    """
    geocoder = _get_geocoding_service()

    if query:
        results = geocoder.geocode_many(query, limit=limit)
        if results:
            return _deduplicate_results(results)
        # Query failed -- fall through to site-based resolution

    # Try reverse geocode from coordinates
    if site.latitude and site.longitude:
        results = geocoder.reverse_geocode_many(float(site.latitude), float(site.longitude), limit=limit)
        if results:
            return _deduplicate_results(results)

    # Fallback to forward geocode from physical address
    if site.physical_address:
        return _deduplicate_results(geocoder.geocode_many(site.physical_address, limit=limit))

    return []


def resolve_site_address(site: Site) -> RIRAddress | None:
    """
    Resolve or return cached structured address for a Site.

    1. If RIRAddress already exists for this Site, return it.
    2. If Site has latitude/longitude, reverse geocode.
    3. Else if Site has physical_address, forward geocode.
    4. If geocoding succeeds, create and return RIRAddress.
    5. If fails, return None.

    Raises SubdivisionCodeError, saving nothing, when the geocoder found a state/province
    whose ISO 3166-2 code cannot be determined.
    """
    from netbox_rir_manager.models import RIRAddress

    # Check for existing cached site-level address
    existing = RIRAddress.get_for_site(site)
    if existing:
        return existing

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

    if result.subdivision_error:
        raise SubdivisionCodeError(result.subdivision_error)

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
