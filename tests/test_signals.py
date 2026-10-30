from unittest.mock import patch

import pytest


@pytest.fixture
def make_parent(rir_config, rir):
    """Build a parent allocation (aggregate plus linked RIRNetwork) for a prefix range."""
    from ipam.models import Aggregate

    from netbox_rir_manager.models import RIRNetwork

    def _make(prefix, auto_reassign=True):
        agg = Aggregate.objects.create(prefix=prefix, rir=rir)
        handle = "NET-" + prefix.replace(".", "-").replace("/", "-")
        return RIRNetwork.objects.create(
            rir_config=rir_config, handle=handle, aggregate=agg, auto_reassign=auto_reassign
        )

    return _make


@pytest.fixture
def removal_opt_in(make_parent):
    """A parent allocation covering the 10/8 test prefixes, opted into automatic reassignment."""
    return make_parent("10.0.0.0/8")


@pytest.mark.django_db
class TestAutoLinkSignal:
    def test_auto_links_aggregate_on_save(self, rir_config, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            raw_data={"net_blocks": [{"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}]},
        )
        net.refresh_from_db()
        assert net.aggregate == agg

    def test_auto_links_prefix_on_save(self, rir_config, rir):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.0.0.0/8")
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-10-0-0-0-1",
            net_name="TEN-NET",
            raw_data={"net_blocks": [{"start_address": "10.0.0.0", "cidr_length": 8, "type": "DS"}]},
        )
        net.refresh_from_db()
        assert net.prefix == pfx

    def test_auto_link_does_not_overwrite_existing(self, rir_config, rir):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        agg2 = Aggregate.objects.create(prefix="10.0.0.0/8", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-192-0-2-0-1",
            net_name="EXAMPLE-NET",
            aggregate=agg2,  # manually set to different aggregate
            raw_data={"net_blocks": [{"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}]},
        )
        net.refresh_from_db()
        assert net.aggregate == agg2  # should NOT be overwritten

    def test_auto_link_disabled_by_setting(self, rir_config, rir, settings):
        from ipam.models import Aggregate

        from netbox_rir_manager.models import RIRNetwork

        settings.PLUGINS_CONFIG = {"netbox_rir_manager": {"auto_link_networks": False}}
        Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DISABLED-1",
            net_name="DISABLED-NET",
            raw_data={"net_blocks": [{"start_address": "192.0.2.0", "cidr_length": 24, "type": "DS"}]},
        )
        net.refresh_from_db()
        assert net.aggregate is None

    def test_no_match_does_nothing(self, rir_config):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-NOMATCH-1",
            net_name="NO-MATCH-NET",
            raw_data={"net_blocks": [{"start_address": "172.16.0.0", "cidr_length": 12, "type": "DS"}]},
        )
        net.refresh_from_db()
        assert net.aggregate is None
        assert net.prefix is None

    def test_empty_raw_data_does_nothing(self, rir_config):
        from netbox_rir_manager.models import RIRNetwork

        net = RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-EMPTY-1",
            net_name="EMPTY-NET",
            raw_data={},
        )
        net.refresh_from_db()
        assert net.aggregate is None
        assert net.prefix is None


@pytest.mark.django_db
class TestPrefixDeleteSignal:
    """Tests for remove_rir_network_on_prefix_delete signal."""

    def test_enqueues_removal_for_child_reassignment(self, rir_config, rir_user_key, removal_opt_in):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.5.0.0/24")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEL-CHILD-1",
            net_name="DEL-CHILD",
            prefix=pfx,
            # aggregate is None -- this is a child reassignment
        )

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.delete()

        mock_job.enqueue.assert_called_once()
        call_kwargs = mock_job.enqueue.call_args[1]
        assert call_kwargs["network_id"] is not None
        assert call_kwargs["user_key_id"] == rir_user_key.pk

    def test_skips_parent_allocation(self, rir_config, rir_user_key, rir):
        """RIRNetwork with both aggregate and prefix set should NOT trigger removal."""
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.6.0.0/20", rir=rir)
        pfx = Prefix.objects.create(prefix="10.6.0.0/20")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEL-PARENT-1",
            net_name="DEL-PARENT",
            prefix=pfx,
            aggregate=agg,  # Has aggregate -- parent allocation
        )

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.delete()

        mock_job.enqueue.assert_not_called()

    def test_warns_when_no_api_key(self, rir_config, removal_opt_in):
        """Deletion proceeds but logs a warning when no API key exists."""
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.7.0.0/24")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEL-NOKEY-1",
            net_name="DEL-NOKEY",
            prefix=pfx,
        )

        with patch("netbox_rir_manager.signals.logger") as mock_logger:
            pfx.delete()  # Should not raise

        mock_logger.warning.assert_called_once()
        assert "no API key" in mock_logger.warning.call_args[0][0]

    def test_no_rir_network_does_nothing(self, rir_config):
        """Deleting a prefix with no linked RIRNetwork should not trigger anything."""
        from ipam.models import Prefix

        pfx = Prefix.objects.create(prefix="10.8.0.0/24")

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.delete()

        mock_job.enqueue.assert_not_called()


@pytest.mark.django_db
class TestAutoReassignStatusGuard:
    """Tests that auto_reassign_prefix only fires for active prefixes."""

    def test_skips_deprecated_prefix(self, rir_user_key, make_parent):
        """A deprecated prefix with site+tenant should NOT trigger reassignment."""
        from ipam.models import Prefix

        make_parent("10.20.0.0/16")

        with patch("netbox_rir_manager.jobs.ReassignJob") as mock_job:
            Prefix.objects.create(prefix="10.20.1.0/24", status="deprecated")

        mock_job.enqueue.assert_not_called()

    def test_skips_reserved_prefix(self, rir_user_key, make_parent):
        """A reserved prefix should NOT trigger reassignment."""
        from ipam.models import Prefix

        make_parent("10.21.0.0/16")

        with patch("netbox_rir_manager.jobs.ReassignJob") as mock_job:
            Prefix.objects.create(prefix="10.21.1.0/24", status="reserved")

        mock_job.enqueue.assert_not_called()

    @pytest.mark.parametrize("config_active, expect_enqueue", [(True, True), (False, False)])
    def test_requires_active_config(self, rir_config, rir_user_key, make_parent, config_active, expect_enqueue):
        """An opted-in parent only triggers auto-reassign while its config is active."""
        from dcim.models import Site
        from ipam.models import Prefix
        from tenancy.models import Tenant

        rir_config.is_active = config_active
        rir_config.save()
        make_parent("10.22.0.0/16")
        site = Site.objects.create(name="Site A", slug="site-a")
        tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a")

        with patch("netbox_rir_manager.jobs.ReassignJob") as mock_job:
            Prefix.objects.create(prefix="10.22.1.0/24", status="active", scope=site, tenant=tenant)

        assert mock_job.enqueue.called is expect_enqueue


@pytest.mark.django_db
class TestPrefixDeactivateSignal:
    """Tests for remove_network_on_prefix_deactivate signal."""

    def test_enqueues_removal_on_deactivation(self, rir_config, rir_user_key, removal_opt_in):
        """Changing prefix to deprecated should enqueue ARIN network removal."""
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.30.0.0/24", status="active")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEACT-1",
            net_name="DEACT-NET",
            prefix=pfx,
        )

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.status = "deprecated"
            pfx.save()

        mock_job.enqueue.assert_called_once()
        call_kwargs = mock_job.enqueue.call_args[1]
        assert call_kwargs["network_id"] is not None
        assert call_kwargs["user_key_id"] == rir_user_key.pk

    def test_skips_active_prefix(self, rir_config, rir_user_key):
        """Saving a prefix that stays active should NOT trigger removal."""
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.31.0.0/24", status="active")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-ACTIVE-1",
            net_name="ACTIVE-NET",
            prefix=pfx,
        )

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.description = "updated"
            pfx.save()

        mock_job.enqueue.assert_not_called()

    def test_skips_newly_created_prefix(self, rir_config, rir_user_key):
        """A newly created deprecated prefix should NOT trigger removal."""
        from ipam.models import Prefix

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            Prefix.objects.create(prefix="10.32.0.0/24", status="deprecated")

        mock_job.enqueue.assert_not_called()

    def test_skips_parent_allocation(self, rir_config, rir_user_key, rir):
        """RIRNetwork with aggregate set should NOT trigger removal on deactivation."""
        from ipam.models import Aggregate, Prefix

        from netbox_rir_manager.models import RIRNetwork

        agg = Aggregate.objects.create(prefix="10.33.0.0/20", rir=rir)
        pfx = Prefix.objects.create(prefix="10.33.0.0/20", status="active")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEACT-PARENT-1",
            net_name="DEACT-PARENT",
            prefix=pfx,
            aggregate=agg,
        )

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            pfx.status = "deprecated"
            pfx.save()

        mock_job.enqueue.assert_not_called()

    def test_warns_when_no_api_key(self, rir_config, removal_opt_in):
        """Deactivation logs a warning when no API key exists."""
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="10.34.0.0/24", status="active")
        RIRNetwork.objects.create(
            rir_config=rir_config,
            handle="NET-DEACT-NOKEY-1",
            net_name="DEACT-NOKEY",
            prefix=pfx,
        )

        with patch("netbox_rir_manager.signals.logger") as mock_logger:
            pfx.status = "deprecated"
            pfx.save()

        mock_logger.warning.assert_called_once()
        assert "no API key" in mock_logger.warning.call_args[0][0]


@pytest.mark.django_db
class TestRemovalRequiresOptIn:
    """Prefix delete/deactivate only removes at ARIN under the parent's auto_reassign opt-in."""

    @pytest.mark.parametrize("change", ["delete", "deactivate"])
    @pytest.mark.parametrize(
        "auto_reassign, config_active",
        [
            pytest.param(False, True, id="parent-not-opted-in"),
            pytest.param(True, False, id="config-inactive"),
            pytest.param(None, True, id="no-parent-network"),
        ],
    )
    def test_leaves_arin_net_in_place(
        self, rir_config, rir_user_key, make_parent, change, auto_reassign, config_active
    ):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        rir_config.is_active = config_active
        rir_config.save()
        if auto_reassign is not None:
            make_parent("10.40.0.0/16", auto_reassign=auto_reassign)
        pfx = Prefix.objects.create(prefix="10.40.1.0/24", status="active")
        RIRNetwork.objects.create(rir_config=rir_config, handle="NET-10-40-1-0-1", prefix=pfx)

        with patch("netbox_rir_manager.jobs.RemoveNetworkJob") as mock_job:
            if change == "delete":
                pfx.delete()
            else:
                pfx.status = "deprecated"
                pfx.save()

        mock_job.enqueue.assert_not_called()
        skipped = RIRSyncLog.objects.get(object_handle="NET-10-40-1-0-1")
        assert skipped.status == "skipped"
        assert skipped.operation == "remove"
