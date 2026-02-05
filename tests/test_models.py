import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestRIRConfig:
    def test_create_rir_config(self, rir):
        from netbox_rir_manager.models import RIRConfig

        config = RIRConfig.objects.create(
            rir=rir,
            name="Test Config",
            org_handle="TESTORG-ARIN",
        )
        assert config.pk is not None
        assert config.name == "Test Config"
        assert config.is_active is True
        assert str(config) == "Test Config"

    def test_rir_config_unique_together(self, rir):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRConfig

        RIRConfig.objects.create(rir=rir, name="Unique Config")
        with pytest.raises(IntegrityError):
            RIRConfig.objects.create(rir=rir, name="Unique Config")

    def test_rir_config_get_absolute_url(self, rir_config):
        url = rir_config.get_absolute_url()
        assert f"/plugins/rir-manager/configs/{rir_config.pk}/" == url

    def test_rir_config_default_values(self, rir):
        from netbox_rir_manager.models import RIRConfig

        config = RIRConfig.objects.create(rir=rir, name="Defaults")
        assert config.api_url == ""
        assert config.org_handle == ""
        assert config.is_active is True
        assert config.last_sync is None

    def test_rir_config_ordering(self, rir):
        from netbox_rir_manager.models import RIRConfig

        b = RIRConfig.objects.create(rir=rir, name="B Config")
        a = RIRConfig.objects.create(rir=rir, name="A Config")
        configs = list(RIRConfig.objects.filter(pk__in=[a.pk, b.pk]))
        assert configs[0].name == "A Config"
        assert configs[1].name == "B Config"

    def test_rir_cascade_delete(self, rir, rir_config):
        from netbox_rir_manager.models import RIRConfig

        assert RIRConfig.objects.filter(pk=rir_config.pk).exists()
        rir.delete()
        assert not RIRConfig.objects.filter(pk=rir_config.pk).exists()


@pytest.mark.django_db
class TestRIROrganization:
    def test_create_rir_organization(self, rir_config):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="EXAMPLE-ARIN",
            name="Example Corp",
            city="Anytown",
            country="US",
        )
        assert org.pk is not None
        assert str(org) == "EXAMPLE-ARIN"

    def test_rir_organization_unique_handle(self, rir_config):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIROrganization

        RIROrganization.objects.create(rir_config=rir_config, handle="DUP-ARIN", name="Org 1")
        with pytest.raises(IntegrityError):
            RIROrganization.objects.create(rir_config=rir_config, handle="DUP-ARIN", name="Org 2")

    def test_rir_organization_get_absolute_url(self, rir_organization):
        url = rir_organization.get_absolute_url()
        assert f"/plugins/rir-manager/organizations/{rir_organization.pk}/" == url

    def test_rir_organization_rir_config_relationship(self, rir_config, rir_organization):
        assert rir_organization.rir_config == rir_config
        assert rir_organization in rir_config.organizations.all()

    def test_rir_organization_cascade_on_rir_config_delete(self, rir_config, rir_organization):
        from netbox_rir_manager.models import RIROrganization

        org_pk = rir_organization.pk
        rir_config.delete()
        assert not RIROrganization.objects.filter(pk=org_pk).exists()

    def test_rir_organization_raw_data(self, rir_config):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="JSONTEST-ARIN",
            name="JSON Test",
            raw_data={"key": "value", "nested": {"a": 1}},
        )
        org.refresh_from_db()
        assert org.raw_data == {"key": "value", "nested": {"a": 1}}


@pytest.mark.django_db
class TestRIRContact:
    def test_create_rir_contact(self, rir_config):
        from netbox_rir_manager.models import RIRContact

        contact = RIRContact.objects.create(
            rir_config=rir_config,
            handle="JD123-ARIN",
            contact_type="PERSON",
            first_name="John",
            last_name="Doe",
            email="jdoe@example.com",
        )
        assert contact.pk is not None
        assert str(contact) == "JD123-ARIN"

    def test_rir_contact_get_absolute_url(self, rir_contact):
        url = rir_contact.get_absolute_url()
        assert f"/plugins/rir-manager/contacts/{rir_contact.pk}/" == url

    def test_rir_contact_organization_set_null(self, rir_contact, rir_organization):

        assert rir_contact.organization == rir_organization
        rir_organization.delete()
        rir_contact.refresh_from_db()
        assert rir_contact.organization is None

    def test_rir_contact_unique_handle(self, rir_config):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRContact

        RIRContact.objects.create(rir_config=rir_config, handle="DUP-ARIN", contact_type="PERSON", last_name="A")
        with pytest.raises(IntegrityError):
            RIRContact.objects.create(rir_config=rir_config, handle="DUP-ARIN", contact_type="ROLE", last_name="B")

    def test_rir_contact_organization_reverse_relation(self, rir_contact, rir_organization):
        assert rir_contact in rir_organization.contacts.all()


@pytest.mark.django_db
class TestRIRContactLink:
    def test_link_to_netbox_contact(self, rir_contact):
        from tenancy.models import Contact

        nb_contact = Contact.objects.create(name="John Doe")
        rir_contact.contact = nb_contact
        rir_contact.save()
        rir_contact.refresh_from_db()
        assert rir_contact.contact == nb_contact

    def test_contact_set_null_on_delete(self, rir_contact):
        from tenancy.models import Contact

        nb_contact = Contact.objects.create(name="Jane Doe")
        rir_contact.contact = nb_contact
        rir_contact.save()
        nb_contact.delete()
        rir_contact.refresh_from_db()
        assert rir_contact.contact is None


@pytest.mark.django_db
class TestRIRNetwork:
    def test_create_rir_network(self, rir_config):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
        )
        assert net.pk is not None
        assert str(net) == "NET-192-0-2-0-1"

    def test_rir_network_link_to_aggregate(self, rir_config, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg,
        )
        assert net.aggregate == agg
        assert net in agg.rir_networks.all()

    def test_rir_network_link_to_prefix(self, rir_config):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        prefix = Prefix.objects.create(prefix="10.0.0.0/8")
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-10-0-0-0-1",
            net_name="TEN-NET",
            prefix=prefix,
        )
        assert net.prefix == prefix
        assert net in prefix.rir_networks.all()

    def test_rir_network_get_absolute_url(self, rir_network):
        url = rir_network.get_absolute_url()
        assert f"/plugins/rir-manager/networks/{rir_network.pk}/" == url

    def test_rir_network_organization_set_null(self, rir_network, rir_organization):

        assert rir_network.organization == rir_organization
        rir_organization.delete()
        rir_network.refresh_from_db()
        assert rir_network.organization is None

    def test_rir_network_aggregate_set_null(self, rir_config, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="172.16.0.0/12", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config, handle="NET-172-16-0-0-1", net_name="RFC1918", aggregate=agg
        )
        agg.delete()
        net.refresh_from_db()
        assert net.aggregate is None


@pytest.mark.django_db
class TestRIRSyncLog:
    def test_create_sync_log(self, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="organization",
            object_handle="EXAMPLE-ARIN",
            status="success",
            message="Synced successfully",
        )
        assert log.pk is not None
        assert str(log) == "sync EXAMPLE-ARIN (success)"

    def test_sync_log_get_absolute_url(self, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="X", status="success"
        )
        url = log.get_absolute_url()
        assert f"/plugins/rir-manager/sync-logs/{log.pk}/" == url

    def test_sync_log_ordering(self, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log1 = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="A", status="success"
        )
        log2 = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="B", status="error"
        )
        logs = list(RIRSyncLog.objects.filter(pk__in=[log1.pk, log2.pk]))
        # Ordered by -created, so log2 (newer) should be first
        assert logs[0].pk == log2.pk
        assert logs[1].pk == log1.pk

    def test_sync_log_cascade_on_rir_config_delete(self, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="X", status="success"
        )
        assert RIRSyncLog.objects.filter(rir_config=rir_config).exists()
        rir_config.delete()
        assert not RIRSyncLog.objects.filter(rir_config_id=rir_config.pk).exists()


@pytest.mark.django_db
class TestSyncedByTracking:
    def test_organization_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="SYNCTEST-ARIN",
            name="Sync Test Org",
            synced_by=rir_user_key,
        )
        org.refresh_from_db()
        assert org.synced_by == rir_user_key

    def test_contact_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIRContact

        contact = RIRContact.objects.create(
            rir_config=rir_config,
            handle="SYNCPOC-ARIN",
            contact_type="PERSON",
            last_name="Test",
            synced_by=rir_user_key,
        )
        contact.refresh_from_db()
        assert contact.synced_by == rir_user_key

    def test_network_synced_by(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="SYNCNET-1",
            net_name="SYNC-NET",
            synced_by=rir_user_key,
        )
        net.refresh_from_db()
        assert net.synced_by == rir_user_key

    def test_synced_by_set_null_on_key_delete(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            rir_config=rir_config,
            handle="NULLTEST-ARIN",
            name="Null Test Org",
            synced_by=rir_user_key,
        )
        rir_user_key.delete()
        org.refresh_from_db()
        assert org.synced_by is None


@pytest.mark.django_db
class TestRIRUserKey:
    def test_create_user_key(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(
            user=admin_user,
            rir_config=rir_config,
            api_key="user-api-key-123",
        )
        assert key.pk is not None
        assert str(key) == f"admin - {rir_config.name}"

    def test_user_key_unique_per_config(self, rir_config, admin_user):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRUserKey

        RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="key1")
        with pytest.raises(IntegrityError):
            RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="key2")

    def test_user_key_get_absolute_url(self, rir_user_key):
        url = rir_user_key.get_absolute_url()
        assert "/user-keys/" in url

    def test_user_key_cascade_on_config_delete(self, rir_user_key, rir_config):
        from netbox_rir_manager.models import RIRUserKey

        rir_config.delete()
        assert not RIRUserKey.objects.filter(pk=rir_user_key.pk).exists()

    def test_user_key_cascade_on_user_delete(self, rir_user_key, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        admin_user.delete()
        assert not RIRUserKey.objects.filter(pk=rir_user_key.pk).exists()


@pytest.mark.django_db
class TestRIRTicket:
    def test_create_ticket(self, rir_config, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-20260205-001",
            ticket_type="IPV4_SIMPLE_REASSIGN",
            status="pending_review",
            network=rir_network,
            submitted_by=rir_user_key,
            created_date=timezone.now(),
        )
        assert str(ticket) == "Ticket TKT-20260205-001"
        assert "/plugins/rir-manager/tickets/" in ticket.get_absolute_url()

    def test_ticket_number_unique(self, rir_config):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRTicket

        RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-UNIQUE",
            ticket_type="NET_DELETE_REQUEST",
            status="pending_review",
            created_date=timezone.now(),
        )
        with pytest.raises(IntegrityError):
            RIRTicket.objects.create(
                rir_config=rir_config,
                ticket_number="TKT-UNIQUE",
                ticket_type="NET_DELETE_REQUEST",
                status="pending_review",
                created_date=timezone.now(),
            )

    def test_ticket_optional_fields(self, rir_config):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-OPTIONAL",
            ticket_type="IPV4_REALLOCATE",
            status="approved",
            created_date=timezone.now(),
        )
        assert ticket.network is None
        assert ticket.submitted_by is None
        assert ticket.resolved_date is None
        assert ticket.resolution == ""

    def test_ticket_with_resolution(self, rir_config, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-RESOLVED",
            ticket_type="IPV4_DETAILED_REASSIGN",
            status="resolved",
            resolution="accepted",
            network=rir_network,
            submitted_by=rir_user_key,
            created_date=timezone.now(),
            resolved_date=timezone.now(),
        )
        assert ticket.resolution == "accepted"
        assert ticket.resolved_date is not None

    def test_ticket_cascade_on_rir_config_delete(self, rir_config):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-CASCADE",
            ticket_type="NET_DELETE_REQUEST",
            status="pending_review",
            created_date=timezone.now(),
        )
        ticket_pk = ticket.pk
        rir_config.delete()
        assert not RIRTicket.objects.filter(pk=ticket_pk).exists()

    def test_ticket_network_set_null(self, rir_config, rir_network):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-NETNULL",
            ticket_type="IPV4_SIMPLE_REASSIGN",
            status="pending_review",
            network=rir_network,
            created_date=timezone.now(),
        )
        rir_network.delete()
        ticket.refresh_from_db()
        assert ticket.network is None

    def test_ticket_submitted_by_set_null(self, rir_config, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="TKT-USERNULL",
            ticket_type="IPV4_SIMPLE_REASSIGN",
            status="pending_review",
            submitted_by=rir_user_key,
            created_date=timezone.now(),
        )
        rir_user_key.delete()
        ticket.refresh_from_db()
        assert ticket.submitted_by is None
