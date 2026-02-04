import django_tables2 as tables
from netbox.tables import NetBoxTable, columns

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountTable(NetBoxTable):
    name = tables.Column(linkify=True)
    rir = tables.Column(linkify=True)
    is_active = columns.BooleanColumn()
    last_sync = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRAccount
        fields = ("pk", "id", "name", "rir", "org_handle", "is_active", "last_sync")
        default_columns = ("name", "rir", "org_handle", "is_active", "last_sync")


class RIROrganizationTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    name = tables.Column()
    account = tables.Column(linkify=True)
    city = tables.Column()
    country = tables.Column()
    last_synced = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIROrganization
        fields = ("pk", "id", "handle", "name", "account", "city", "country", "last_synced")
        default_columns = ("handle", "name", "account", "city", "country", "last_synced")


class RIRContactTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    last_name = tables.Column()
    first_name = tables.Column()
    contact_type = tables.Column()
    company_name = tables.Column()
    email = tables.Column()
    organization = tables.Column(linkify=True)
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
            "organization",
            "last_synced",
        )
        default_columns = ("handle", "contact_type", "first_name", "last_name", "email", "organization")


class RIRNetworkTable(NetBoxTable):
    handle = tables.Column(linkify=True)
    net_name = tables.Column()
    organization = tables.Column(linkify=True)
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
            "organization",
            "aggregate",
            "prefix",
            "last_synced",
        )
        default_columns = ("handle", "net_name", "organization", "aggregate", "prefix", "last_synced")


class RIRSyncLogTable(NetBoxTable):
    account = tables.Column(linkify=True)
    operation = tables.Column()
    object_type = tables.Column()
    object_handle = tables.Column()
    status = tables.Column()
    message = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = RIRSyncLog
        fields = ("pk", "id", "account", "operation", "object_type", "object_handle", "status", "message", "created")
        default_columns = ("account", "operation", "object_type", "object_handle", "status", "created")
