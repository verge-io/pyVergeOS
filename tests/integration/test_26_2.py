"""Live coverage for VergeOS 26.2 fields.

Reads are safe to repeat. The one write flips ``dhcp_broadcast`` on a
disposable network and puts it back. Time mode, package uninstall, and
VixDiskLib installs are left alone because they change the running system.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
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
        assert settings.key == 1
        assert settings.mode in ("ntp", "ptp")
        assert isinstance(settings.ntp_servers, str)

    def test_time_dashboard(self, live_client: VergeClient) -> None:
        """Read node sync status from the time dashboard."""
        _needs_26_2(live_client)
        dashboard = live_client.time_dashboard.get()
        assert isinstance(dashboard.nodes, list)
        assert isinstance(dashboard.alarms, list)

    def test_vm_and_status_fields(self, live_client: VergeClient) -> None:
        """Listing VMs requests the 26.2 columns, including machine status."""
        _needs_26_2(live_client)
        vms = live_client.vms.list(limit=1)
        if not vms:
            pytest.skip("no VMs on this system")
        vm = vms[0]
        assert isinstance(vm.bios_serial, str)
        assert vm.vgamem_mb is None or isinstance(vm.vgamem_mb, int)
        status = vm.machine_status.get()
        assert isinstance(status.agent_ip_list, list)
        assert isinstance(status.time_sync_status, str)

    def test_catalog_and_package_fields(self, live_client: VergeClient) -> None:
        """Files, alarms, and packages accept their 26.2 columns."""
        _needs_26_2(live_client)
        files = live_client.files.list(limit=1)
        if files:
            assert isinstance(files[0].uuid, str)
        alarms = live_client.alarms.list(limit=1)
        if alarms:
            assert isinstance(alarms[0].sub_owner_type, str)
        packages = live_client.update_packages.list(limit=1)
        if packages:
            assert isinstance(packages[0].dependencies, list)
        settings = live_client.update_settings.get()
        assert isinstance(settings.restart_pending_packages, bool)

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
