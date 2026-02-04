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
