from netbox.search import SearchIndex, register_search

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization


@register_search
class RIRAccountIndex(SearchIndex):
    model = RIRAccount
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
        ("email", 300),
    )


@register_search
class RIRNetworkIndex(SearchIndex):
    model = RIRNetwork
    fields = (
        ("handle", 100),
        ("net_name", 200),
    )
