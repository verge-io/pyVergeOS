"""Live coverage for VergeOS 26.2 fields.

Reads are safe to repeat. The one write flips ``dhcp_broadcast`` on a
disposable network and puts it back. Time mode, package uninstall, and
VixDiskLib installs are left alone because they change the running system.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.routing import VNET_BGP_DAEMONS
from pyvergeos.resources.vms import VGAMEM_CHOICES
from pyvergeos.versions import version_at_least
from tests.integration.live_support import create_disposable_network, destroy_network


def _needs_26_2(client: VergeClient) -> None:
    if not version_at_least(client.os_version, 26, 2):
        pytest.skip(f"server {client.os_version} is older than 26.2")


@pytest.mark.integration
class TestVergeOS262:
    """Representative reads, plus one reversible network update."""

    def test_time_settings(self, live_client: VergeClient) -> None:
        """Read the NTP/PTP singleton."""
        _needs_26_2(live_client)
        settings = live_client.time_settings.get()
        assert settings.key == "self"
        assert settings.mode in ("ntp", "ptp")
        assert settings.ntp_servers
        assert settings.ntp_maxclock > 0
        assert settings.ntp_minclock > 0
        assert settings.ntp_minsane > 0
        assert "ntp_maxclock" in settings
        assert "ptp_use_hw_timestamps" in settings

    def test_time_dashboard(self, live_client: VergeClient) -> None:
        """Read node sync status from the time dashboard."""
        _needs_26_2(live_client)
        dashboard = live_client.time_dashboard.get()
        assert dashboard.settings
        assert dashboard.mode in ("ntp", "ptp")
        assert dashboard.mode == dashboard.settings.get("mode")
        assert dashboard.nodes
        states = [node.time_sync_status for node in dashboard.nodes]
        assert all(isinstance(state, (dict, list)) for state in states)
        assert any(isinstance(state, dict) and state for state in states)

    def test_vm_and_status_fields(self, live_client: VergeClient) -> None:
        """Listing VMs requests the 26.2 columns, including machine status."""
        _needs_26_2(live_client)
        vms = live_client.vms.list(limit=5)
        if not vms:
            pytest.skip("no VMs on this system")
        vm = vms[0]
        assert "bios_serial" in vm
        assert isinstance(vm.bios_serial, str)
        assert vm.vgamem_mb in VGAMEM_CHOICES
        status = vm.machine_status.get()
        assert isinstance(status.agent_ip_list, str)
        assert isinstance(status.time_sync_status, (dict, list))

    def test_catalog_and_package_fields(self, live_client: VergeClient) -> None:
        """Files, alarms, and packages accept their 26.2 columns."""
        _needs_26_2(live_client)
        alarms = live_client.alarms.list(limit=1)
        if alarms:
            assert isinstance(alarms[0].sub_owner_type, str)
        packages = live_client.update_packages.list(limit=1)
        if packages:
            assert "dependencies" in packages[0]
            assert isinstance(packages[0].dependencies, list)
        settings = live_client.update_settings.get()
        assert "restart_pending_packages" in settings
        assert isinstance(settings.restart_pending_packages, list)

    def test_bgp_config_columns(self, live_client: VergeClient) -> None:
        """Advanced BGP columns are read from vnet_bgp when a row exists."""
        _needs_26_2(live_client)
        found = False
        for network in live_client.networks.list(limit=50):
            config = network.routing.get_config()
            if config is None:
                continue
            found = True
            assert "advanced" in config
            assert "advanced_config" in config
            assert "console_rows" in config
            assert "console_cols" in config
            assert "console_status" not in config
            assert isinstance(config.advanced_config, str)
            if config.advanced:
                assert config.advanced_config
            assert "daemon_bgpd" in config
            for name in VNET_BGP_DAEMONS:
                assert f"daemon_{name}" in config
            break
        if not found:
            pytest.skip("no vnet_bgp row on this system")

    def test_bond_interfaces_and_vmware(self, live_client: VergeClient) -> None:
        """Bond members and VMware containers can be listed."""
        _needs_26_2(live_client)
        members = live_client.vnet_bond_interfaces.list(limit=1)
        assert isinstance(members, list)
        containers = live_client.vmware_containers.list(limit=1)
        assert isinstance(containers, list)

    def test_dhcp_broadcast_round_trip(self, live_client: VergeClient) -> None:
        """Set dhcp_broadcast on a disposable network, then clear it."""
        _needs_26_2(live_client)
        network = create_disposable_network(live_client, prefix="pytest-262")
        try:
            live_client.networks.update(network.key, dhcp_broadcast=True)
            refreshed = live_client.networks.get(network.key)
            assert refreshed.dhcp_broadcast is True
            live_client.networks.update(network.key, dhcp_broadcast=False)
            cleared = live_client.networks.get(network.key)
            assert cleared.dhcp_broadcast is False
        finally:
            destroy_network(live_client, network)
