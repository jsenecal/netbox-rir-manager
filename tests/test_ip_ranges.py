import ipaddress

import netaddr
import pytest

from netbox_rir_manager.ip_ranges import prefix_range

CASES = [
    pytest.param("192.0.2.0/24", ("192.0.2.0", "192.0.2.255"), id="ipv4-24"),
    pytest.param("192.0.2.8/31", ("192.0.2.8", "192.0.2.9"), id="ipv4-31"),
    pytest.param("192.0.2.8/32", ("192.0.2.8", "192.0.2.8"), id="ipv4-32"),
    pytest.param("2001:db8::/64", ("2001:db8::", "2001:db8::ffff:ffff:ffff:ffff"), id="ipv6-64"),
    pytest.param("2001:db8::/127", ("2001:db8::", "2001:db8::1"), id="ipv6-127"),
    pytest.param("2001:db8::/128", ("2001:db8::", "2001:db8::"), id="ipv6-128"),
]


class TestPrefixRange:
    """prefix_range returns the first and last address for every prefix length (#55)."""

    @pytest.mark.parametrize("prefix, expected", CASES)
    @pytest.mark.parametrize(
        "kind", [str, netaddr.IPNetwork, ipaddress.ip_network], ids=["str", "netaddr", "ipaddress"]
    )
    def test_first_and_last_address(self, prefix, expected, kind):
        assert prefix_range(kind(prefix)) == expected

    def test_host_bits_are_ignored(self):
        assert prefix_range(netaddr.IPNetwork("192.0.2.9/31")) == ("192.0.2.8", "192.0.2.9")
