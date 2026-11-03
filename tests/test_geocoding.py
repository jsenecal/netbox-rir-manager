"""Geocoding: mapping Nominatim results to RIRAddress fields. Nominatim is always mocked."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

GET_GEOCODER = "netbox_rir_manager.services.geocoding.NominatimGeocoder._get_geocoder"


def nominatim_location(country_code, **address):
    """A geopy Location stand-in carrying a Nominatim addressdetails response."""
    address = {"country_code": country_code, "road": "Main Street", "house_number": "1", "city": "Town", **address}
    return SimpleNamespace(raw={"display_name": "1 Main Street, Town", "address": address})


def mock_nominatim(location):
    """Patch the geopy client so every forward and reverse lookup returns location."""
    client = MagicMock()
    client.geocode.return_value = location
    client.reverse.return_value = location
    return patch(GET_GEOCODER, return_value=client)


DE_NW_LONG_NAME = {"state": "North Rhine-Westphalia"}


class TestStateCode:
    """The subdivision stored is the ISO 3166-2 code without its country prefix, as ARIN takes it."""

    @pytest.mark.parametrize(
        "country, address, expected",
        [
            pytest.param("de", {**DE_NW_LONG_NAME, "ISO3166-2-lvl4": "DE-NW"}, "NW", id="nominatim-iso-code"),
            pytest.param("ca", {"state": "British Columbia"}, "BC", id="pycountry-name"),
            pytest.param("ca", {"state": "british columbia"}, "BC", id="pycountry-name-any-case"),
            pytest.param("de", {"state": "Bavaria"}, "BY", id="pycountry-english-name"),
            pytest.param("fr", {"state": "Somewhere", "ISO3166-2-lvl6": "FR-75"}, "75", id="nominatim-lvl6"),
            pytest.param("de", {"state": "Bavaria", "ISO3166-2-lvl4": "US-NY"}, "BY", id="other-country-code-ignored"),
            pytest.param("sg", {}, "", id="no-subdivision"),
            pytest.param("", {"ISO3166-2-lvl4": "DE-NW"}, "", id="no-country"),
        ],
    )
    def test_geocode_maps_subdivision(self, country, address, expected):
        from netbox_rir_manager.services.geocoding import NominatimGeocoder

        with mock_nominatim(nominatim_location(country, **address)):
            result = NominatimGeocoder().geocode("1 Main Street")

        assert result.state_province == expected
        assert result.subdivision_error == ""

    def test_unmappable_name_is_not_kept(self):
        """Issue #83: an unmapped name is never passed off as a subdivision code."""
        from netbox_rir_manager.services.geocoding import NominatimGeocoder

        with mock_nominatim(nominatim_location("de", **DE_NW_LONG_NAME)):
            result = NominatimGeocoder().geocode("1 Main Street")

        assert result.state_province == ""
        assert result.state_name == "North Rhine-Westphalia"
        assert result.subdivision_error == (
            "Could not determine the ISO 3166-2 subdivision code for 'North Rhine-Westphalia'; "
            "enter it on the Site's RIR address."
        )

    def test_candidates_carry_the_code(self):
        from netbox_rir_manager.services.geocoding import NominatimGeocoder

        location = nominatim_location("de", **DE_NW_LONG_NAME, **{"ISO3166-2-lvl4": "DE-NW"})
        with mock_nominatim(location) as get_geocoder:
            get_geocoder.return_value.geocode.return_value = [location]
            results = NominatimGeocoder().geocode_many("1 Main Street")

        assert [r.state_province for r in results] == ["NW"]


@pytest.mark.django_db
class TestResolveSiteAddress:
    @pytest.fixture
    def site(self):
        from dcim.models import Site

        return Site.objects.create(name="Site G", slug="site-g", physical_address="1 Main Street, Town")

    def test_stores_nominatim_iso_code(self, site):
        """Issue #83: North Rhine-Westphalia is stored as NW, not as the over-long English name."""
        from netbox_rir_manager.services.geocoding import resolve_site_address

        location = nominatim_location("de", **DE_NW_LONG_NAME, **{"ISO3166-2-lvl4": "DE-NW"})
        with mock_nominatim(location):
            address = resolve_site_address(site)

        address.refresh_from_db()
        assert (address.state_province, address.country, address.site) == ("NW", "DE", site)

    def test_short_mapped_name_still_works(self, site):
        from netbox_rir_manager.services.geocoding import resolve_site_address

        with mock_nominatim(nominatim_location("ca", state="British Columbia")):
            address = resolve_site_address(site)

        assert (address.state_province, address.country) == ("BC", "CA")

    def test_unmappable_name_raises_clean_error(self, site):
        """Issue #83: no DataError and no address saved when the code cannot be determined."""
        from netbox_rir_manager.models import RIRAddress
        from netbox_rir_manager.services.geocoding import SubdivisionCodeError, resolve_site_address

        with (
            mock_nominatim(nominatim_location("de", **DE_NW_LONG_NAME)),
            pytest.raises(SubdivisionCodeError, match="'North Rhine-Westphalia'; enter it on the Site's RIR"),
        ):
            resolve_site_address(site)

        assert not RIRAddress.objects.exists()
