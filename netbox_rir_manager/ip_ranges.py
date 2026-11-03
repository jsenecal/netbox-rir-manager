"""Address ranges of IP prefixes, as ARIN's net lookups and reassignments expect them."""

import ipaddress


def prefix_range(prefix):
    """Return (first, last) address of a prefix as strings.

    prefix may be a netaddr.IPNetwork (what Prefix.prefix and Aggregate.prefix hold), an
    ipaddress network, or a CIDR string; host bits are ignored. The last address is taken by
    index rather than from a broadcast attribute: netaddr reports no broadcast address for
    IPv4 /31 and /32 or IPv6 /127 and /128, yet those prefixes still span one or two addresses.
    """
    network = ipaddress.ip_network(str(prefix), strict=False)
    return str(network[0]), str(network[-1])
