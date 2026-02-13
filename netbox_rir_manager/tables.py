import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from netbox_rir_manager.models import (
    RIRConfig,
    RIRContact,
    RIRCustomer,
    RIRNetwork,
    RIROrganization,
    RIRSiteAddress,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)

RIRCONFIG_SYNC_BUTTON = """
{% load helpers %}
<button class="btn btn-sm btn-info" type="submit" title="Sync" formmethod="post"
  formaction="{% url 'plugins:netbox_rir_manager:rirconfig_sync' record.pk %}?return_url={{ request.get_full_path|urlencode }}">
    <i class="mdi mdi-sync"></i>
</button>
"""  # noqa: E501


class RIRConfigTable(NetBoxTable):
    name = tables.Column(linkify=True)
    rir = tables.Column(linkify=True)
    is_active = columns.BooleanColumn()
    last_sync = columns.DateTimeColumn()
    actions = columns.ActionsColumn(
        actions=("edit", "delete", "changelog"),
        extra_buttons=RIRCONFIG_SYNC_BUTTON,
    )

    class Meta(NetBoxTable.Meta):
        model = RIRConfig
        fields = ("pk", "id", "name", "rir", "org_handle", "is_active", "last_sync")
        default_columns = ("name", "rir", "org_handle", "is_active", "last_sync")


class RIROrganizationTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    name = tables.Column()
    rir_config = tables.Column(linkify=True)
    tenant = tables.Column(linkify=True)
    city = tables.Column()
    country = tables.Column()
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIROrganization
        fields = ("pk", "id", "handle", "name", "rir_config", "tenant", "city", "country", "last_synced")
        default_columns = ("handle", "name", "rir_config", "tenant", "city", "country", "last_synced")


class RIRContactTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    last_name = tables.Column()
    first_name = tables.Column()
    contact_type = tables.Column()
    company_name = tables.Column()
    email = tables.Column()
    phone = tables.Column()
    city = tables.Column()
    country = tables.Column()
    organization = tables.Column(linkify=True)
    contact = tables.Column(linkify=True)
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRContact
        fields = (
            "pk",
            "id",
            "handle",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "phone",
            "city",
            "country",
            "organization",
            "contact",
            "last_synced",
        )
        default_columns = ("handle", "contact_type", "first_name", "last_name", "company_name", "organization")


class RIRCustomerTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    customer_name = tables.Column()
    rir_config = tables.Column(linkify=True)
    network = tables.Column(linkify=True)
    tenant = tables.Column(linkify=True)
    city = tables.Column()
    country = tables.Column()
    created_date = columns.DateTimeColumn()
    actions = columns.ActionsColumn(actions=("delete", "changelog"))

    class Meta(NetBoxTable.Meta):
        model = RIRCustomer
        fields = (
            "pk",
            "id",
            "handle",
            "customer_name",
            "rir_config",
            "network",
            "tenant",
            "city",
            "country",
            "created_date",
        )
        default_columns = ("handle", "customer_name", "network", "tenant", "city", "country", "created_date")


class RIRNetworkTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    net_name = tables.Column()
    net_type = tables.Column()
    organization = tables.Column(linkify=True)
    auto_reassign = columns.BooleanColumn()
    aggregate = tables.Column(linkify=True)
    prefix = tables.Column(linkify=True)
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRNetwork
        fields = (
            "pk",
            "id",
            "handle",
            "net_name",
            "net_type",
            "organization",
            "auto_reassign",
            "aggregate",
            "prefix",
            "last_synced",
        )
        default_columns = (
            "handle",
            "net_name",
            "net_type",
            "organization",
            "auto_reassign",
            "aggregate",
            "prefix",
            "last_synced",
        )


class RIRSiteAddressTable(NetBoxTable):
    site = tables.Column(linkify=True)
    city = tables.Column()
    state_province = tables.Column()
    country = tables.Column()
    auto_resolved = columns.BooleanColumn()
    last_resolved = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRSiteAddress
        fields = ("pk", "id", "site", "city", "state_province", "country", "auto_resolved", "last_resolved")
        default_columns = ("site", "city", "state_province", "country", "auto_resolved", "last_resolved")


class RIRSyncLogTable(NetBoxTable):
    rir_config = tables.Column(linkify=True)
    operation = tables.Column()
    object_type = tables.Column()
    object_handle = tables.Column()
    status = tables.Column()
    message = tables.Column()
    actions = columns.ActionsColumn(actions=("delete", "changelog"))

    class Meta(NetBoxTable.Meta):
        model = RIRSyncLog
        fields = ("pk", "id", "rir_config", "operation", "object_type", "object_handle", "status", "message", "created")
        default_columns = ("rir_config", "operation", "object_type", "object_handle", "status", "created")


class RIRTicketTable(NetBoxTable):
    ticket_number = tables.Column(linkify=True)
    ticket_type = tables.Column()
    status = tables.Column()
    resolution = tables.Column()
    rir_config = tables.Column(linkify=True)
    network = tables.Column(linkify=True)
    created_date = columns.DateTimeColumn()
    actions = columns.ActionsColumn(actions=("delete", "changelog"))

    class Meta(NetBoxTable.Meta):
        model = RIRTicket
        fields = (
            "pk",
            "id",
            "ticket_number",
            "ticket_type",
            "status",
            "resolution",
            "rir_config",
            "network",
            "created_date",
        )
        default_columns = (
            "ticket_number",
            "ticket_type",
            "status",
            "rir_config",
            "network",
            "created_date",
        )


class RIRUserKeyTable(NetBoxTable):
    user = tables.Column(linkify=True)
    rir_config = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = RIRUserKey
        fields = ("pk", "id", "user", "rir_config")
        default_columns = ("user", "rir_config")
