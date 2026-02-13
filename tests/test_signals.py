from unittest.mock import patch

import pytest


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

    def test_enqueues_removal_for_child_reassignment(self, rir_config, rir_user_key):
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

    def test_warns_when_no_api_key(self, rir_config):
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
