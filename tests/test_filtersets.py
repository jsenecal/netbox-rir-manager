import pytest


@pytest.mark.django_db
class TestRIRAccountFilterSet:
    def test_search_by_name(self, rir_account):
        from netbox_rir_manager.filtersets import RIRAccountFilterSet
        from netbox_rir_manager.models import RIRAccount

        qs = RIRAccount.objects.all()
        fs = RIRAccountFilterSet({"q": "ARIN"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_search_no_match(self, rir_account):
        from netbox_rir_manager.filtersets import RIRAccountFilterSet
        from netbox_rir_manager.models import RIRAccount

        qs = RIRAccount.objects.all()
        fs = RIRAccountFilterSet({"q": "nonexistent"}, queryset=qs)
        assert fs.qs.count() == 0

    def test_filter_by_active(self, rir, rir_account):
        from netbox_rir_manager.filtersets import RIRAccountFilterSet
        from netbox_rir_manager.models import RIRAccount

        RIRAccount.objects.create(rir=rir, name="Inactive", api_key="key", is_active=False)
        qs = RIRAccount.objects.all()

        fs = RIRAccountFilterSet({"is_active": True}, queryset=qs)
        assert fs.qs.count() == 1
        assert fs.qs.first().name == rir_account.name

        fs = RIRAccountFilterSet({"is_active": False}, queryset=qs)
        assert fs.qs.count() == 1
        assert fs.qs.first().name == "Inactive"


@pytest.mark.django_db
class TestRIROrganizationFilterSet:
    def test_search_by_handle(self, rir_organization):
        from netbox_rir_manager.filtersets import RIROrganizationFilterSet
        from netbox_rir_manager.models import RIROrganization

        qs = RIROrganization.objects.all()
        fs = RIROrganizationFilterSet({"q": "TESTORG"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_search_by_name(self, rir_organization):
        from netbox_rir_manager.filtersets import RIROrganizationFilterSet
        from netbox_rir_manager.models import RIROrganization

        qs = RIROrganization.objects.all()
        fs = RIROrganizationFilterSet({"q": "Test Organization"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_filter_by_account(self, rir_organization, rir_account):
        from netbox_rir_manager.filtersets import RIROrganizationFilterSet
        from netbox_rir_manager.models import RIROrganization

        qs = RIROrganization.objects.all()
        fs = RIROrganizationFilterSet({"account_id": [rir_account.pk]}, queryset=qs)
        assert fs.qs.count() == 1


@pytest.mark.django_db
class TestRIRContactFilterSet:
    def test_search_by_handle(self, rir_contact):
        from netbox_rir_manager.filtersets import RIRContactFilterSet
        from netbox_rir_manager.models import RIRContact

        qs = RIRContact.objects.all()
        fs = RIRContactFilterSet({"q": "JD123"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_search_by_last_name(self, rir_contact):
        from netbox_rir_manager.filtersets import RIRContactFilterSet
        from netbox_rir_manager.models import RIRContact

        qs = RIRContact.objects.all()
        fs = RIRContactFilterSet({"q": "Doe"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_filter_by_contact_type(self, rir_contact):
        from netbox_rir_manager.filtersets import RIRContactFilterSet
        from netbox_rir_manager.models import RIRContact

        qs = RIRContact.objects.all()
        fs = RIRContactFilterSet({"contact_type": "PERSON"}, queryset=qs)
        assert fs.qs.count() == 1

        fs = RIRContactFilterSet({"contact_type": "ROLE"}, queryset=qs)
        assert fs.qs.count() == 0


@pytest.mark.django_db
class TestRIRNetworkFilterSet:
    def test_search_by_handle(self, rir_network):
        from netbox_rir_manager.filtersets import RIRNetworkFilterSet
        from netbox_rir_manager.models import RIRNetwork

        qs = RIRNetwork.objects.all()
        fs = RIRNetworkFilterSet({"q": "NET-192"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_search_by_net_name(self, rir_network):
        from netbox_rir_manager.filtersets import RIRNetworkFilterSet
        from netbox_rir_manager.models import RIRNetwork

        qs = RIRNetwork.objects.all()
        fs = RIRNetworkFilterSet({"q": "EXAMPLE"}, queryset=qs)
        assert fs.qs.count() == 1


@pytest.mark.django_db
class TestRIRSyncLogFilterSet:
    def test_search_by_handle(self, rir_account):
        from netbox_rir_manager.filtersets import RIRSyncLogFilterSet
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="SEARCHME", status="success"
        )
        qs = RIRSyncLog.objects.all()
        fs = RIRSyncLogFilterSet({"q": "SEARCHME"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_filter_by_operation(self, rir_account):
        from netbox_rir_manager.filtersets import RIRSyncLogFilterSet
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="A", status="success"
        )
        RIRSyncLog.objects.create(
            account=rir_account, operation="create", object_type="org", object_handle="B", status="success"
        )
        qs = RIRSyncLog.objects.all()
        fs = RIRSyncLogFilterSet({"operation": "sync"}, queryset=qs)
        assert fs.qs.count() == 1

    def test_filter_by_status(self, rir_account):
        from netbox_rir_manager.filtersets import RIRSyncLogFilterSet
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="A", status="success"
        )
        RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="B", status="error"
        )
        qs = RIRSyncLog.objects.all()
        fs = RIRSyncLogFilterSet({"status": "error"}, queryset=qs)
        assert fs.qs.count() == 1
