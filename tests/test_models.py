import pytest


@pytest.mark.django_db
class TestRIRAccount:
    def test_create_rir_account(self, rir):
        from netbox_rir_manager.models import RIRAccount

        account = RIRAccount.objects.create(
            rir=rir,
            name="Test Account",
            api_key="secret-key-123",
            org_handle="TESTORG-ARIN",
        )
        assert account.pk is not None
        assert account.name == "Test Account"
        assert account.is_active is True
        assert str(account) == "Test Account"

    def test_rir_account_unique_together(self, rir):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRAccount

        RIRAccount.objects.create(rir=rir, name="Unique Account", api_key="key1")
        with pytest.raises(IntegrityError):
            RIRAccount.objects.create(rir=rir, name="Unique Account", api_key="key2")

    def test_rir_account_get_absolute_url(self, rir_account):
        url = rir_account.get_absolute_url()
        assert f"/plugins/rir-manager/accounts/{rir_account.pk}/" == url

    def test_rir_account_default_values(self, rir):
        from netbox_rir_manager.models import RIRAccount

        account = RIRAccount.objects.create(rir=rir, name="Defaults", api_key="key")
        assert account.api_url == ""
        assert account.org_handle == ""
        assert account.is_active is True
        assert account.last_sync is None

    def test_rir_account_ordering(self, rir):
        from netbox_rir_manager.models import RIRAccount

        b = RIRAccount.objects.create(rir=rir, name="B Account", api_key="key1")
        a = RIRAccount.objects.create(rir=rir, name="A Account", api_key="key2")
        accounts = list(RIRAccount.objects.filter(pk__in=[a.pk, b.pk]))
        assert accounts[0].name == "A Account"
        assert accounts[1].name == "B Account"

    def test_rir_cascade_delete(self, rir, rir_account):
        from netbox_rir_manager.models import RIRAccount

        assert RIRAccount.objects.filter(pk=rir_account.pk).exists()
        rir.delete()
        assert not RIRAccount.objects.filter(pk=rir_account.pk).exists()


@pytest.mark.django_db
class TestRIROrganization:
    def test_create_rir_organization(self, rir_account):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            account=rir_account,
            handle="EXAMPLE-ARIN",
            name="Example Corp",
            city="Anytown",
            country="US",
        )
        assert org.pk is not None
        assert str(org) == "EXAMPLE-ARIN"

    def test_rir_organization_unique_handle(self, rir_account):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIROrganization

        RIROrganization.objects.create(account=rir_account, handle="DUP-ARIN", name="Org 1")
        with pytest.raises(IntegrityError):
            RIROrganization.objects.create(account=rir_account, handle="DUP-ARIN", name="Org 2")

    def test_rir_organization_get_absolute_url(self, rir_organization):
        url = rir_organization.get_absolute_url()
        assert f"/plugins/rir-manager/organizations/{rir_organization.pk}/" == url

    def test_rir_organization_account_relationship(self, rir_account, rir_organization):
        assert rir_organization.account == rir_account
        assert rir_organization in rir_account.organizations.all()

    def test_rir_organization_cascade_on_account_delete(self, rir_account, rir_organization):
        from netbox_rir_manager.models import RIROrganization

        org_pk = rir_organization.pk
        rir_account.delete()
        assert not RIROrganization.objects.filter(pk=org_pk).exists()

    def test_rir_organization_raw_data(self, rir_account):
        from netbox_rir_manager.models import RIROrganization

        org = RIROrganization.objects.create(
            account=rir_account,
            handle="JSONTEST-ARIN",
            name="JSON Test",
            raw_data={"key": "value", "nested": {"a": 1}},
        )
        org.refresh_from_db()
        assert org.raw_data == {"key": "value", "nested": {"a": 1}}


@pytest.mark.django_db
class TestRIRContact:
    def test_create_rir_contact(self, rir_account):
        from netbox_rir_manager.models import RIRContact

        contact = RIRContact.objects.create(
            account=rir_account,
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
        from netbox_rir_manager.models import RIRContact

        assert rir_contact.organization == rir_organization
        rir_organization.delete()
        rir_contact.refresh_from_db()
        assert rir_contact.organization is None

    def test_rir_contact_unique_handle(self, rir_account):
        from django.db import IntegrityError

        from netbox_rir_manager.models import RIRContact

        RIRContact.objects.create(account=rir_account, handle="DUP-ARIN", contact_type="PERSON", last_name="A")
        with pytest.raises(IntegrityError):
            RIRContact.objects.create(account=rir_account, handle="DUP-ARIN", contact_type="ROLE", last_name="B")

    def test_rir_contact_organization_reverse_relation(self, rir_contact, rir_organization):
        assert rir_contact in rir_organization.contacts.all()


@pytest.mark.django_db
class TestRIRNetwork:
    def test_create_rir_network(self, rir_account):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            account=rir_account,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
        )
        assert net.pk is not None
        assert str(net) == "NET-192-0-2-0-1"

    def test_rir_network_link_to_aggregate(self, rir_account, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            account=rir_account,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg,
        )
        assert net.aggregate == agg
        assert net in agg.rir_networks.all()

    def test_rir_network_link_to_prefix(self, rir_account):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        prefix = Prefix.objects.create(prefix="10.0.0.0/8")
        net = RIRNetwork.objects.create(
            account=rir_account,
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
        from netbox_rir_manager.models import RIRNetwork

        assert rir_network.organization == rir_organization
        rir_organization.delete()
        rir_network.refresh_from_db()
        assert rir_network.organization is None

    def test_rir_network_aggregate_set_null(self, rir_account, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="172.16.0.0/12", rir=rir)
        net = RIRNetwork.objects.create(
            account=rir_account, handle="NET-172-16-0-0-1", net_name="RFC1918", aggregate=agg
        )
        agg.delete()
        net.refresh_from_db()
        assert net.aggregate is None


@pytest.mark.django_db
class TestRIRSyncLog:
    def test_create_sync_log(self, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            account=rir_account,
            operation="sync",
            object_type="organization",
            object_handle="EXAMPLE-ARIN",
            status="success",
            message="Synced successfully",
        )
        assert log.pk is not None
        assert str(log) == "sync EXAMPLE-ARIN (success)"

    def test_sync_log_get_absolute_url(self, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="X", status="success"
        )
        url = log.get_absolute_url()
        assert f"/plugins/rir-manager/sync-logs/{log.pk}/" == url

    def test_sync_log_ordering(self, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log1 = RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="A", status="success"
        )
        log2 = RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="B", status="error"
        )
        logs = list(RIRSyncLog.objects.filter(pk__in=[log1.pk, log2.pk]))
        # Ordered by -created, so log2 (newer) should be first
        assert logs[0].pk == log2.pk
        assert logs[1].pk == log1.pk

    def test_sync_log_cascade_on_account_delete(self, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="X", status="success"
        )
        assert RIRSyncLog.objects.filter(account=rir_account).exists()
        rir_account.delete()
        assert not RIRSyncLog.objects.filter(account_id=rir_account.pk).exists()
