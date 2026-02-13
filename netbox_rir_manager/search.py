from netbox.search import SearchIndex, register_search

from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization, RIRSiteAddress, RIRTicket


@register_search
class RIRConfigIndex(SearchIndex):
    model = RIRConfig
    fields = (
        ("name", 100),
        ("org_handle", 150),
    )


@register_search
class RIROrganizationIndex(SearchIndex):
    model = RIROrganization
    fields = (
        ("handle", 100),
        ("name", 200),
    )


@register_search
class RIRContactIndex(SearchIndex):
    model = RIRContact
    fields = (
        ("handle", 100),
        ("last_name", 200),
        ("first_name", 200),
        ("company_name", 300),
        ("email", 300),
    )


@register_search
class RIRNetworkIndex(SearchIndex):
    model = RIRNetwork
    fields = (
        ("handle", 100),
        ("net_name", 200),
        ("net_type", 300),
    )


@register_search
class RIRSiteAddressIndex(SearchIndex):
    model = RIRSiteAddress
    fields = (
        ("city", 100),
        ("country", 200),
    )


@register_search
class RIRTicketIndex(SearchIndex):
    model = RIRTicket
    fields = (("ticket_number", 100),)
