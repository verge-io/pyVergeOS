"""VergeOS 26.2 fields, actions, and version-gated default projections."""

from __future__ import annotations

from typing import Any, get_args
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.alarms import Alarm, AlarmManager
from pyvergeos.resources.bond_interfaces import VnetBondInterfaceManager
from pyvergeos.resources.clusters import CPU_TYPES
from pyvergeos.resources.drives import DriveManager
from pyvergeos.resources.files import FILE_TYPES, FileManager
from pyvergeos.resources.machine_stats import MachineStatus, MachineStatusManager
from pyvergeos.resources.networks import Network, NetworkManager
from pyvergeos.resources.nics import MAX_NICS_PER_MACHINE, NICManager
from pyvergeos.resources.queries import VNetQueryType
from pyvergeos.resources.routing import VNET_BGP_26_2_FIELDS, NetworkRoutingManager
from pyvergeos.resources.site_syncs import SiteSyncIncoming, SiteSyncOutgoing
from pyvergeos.resources.time import (
    TIME_SETTINGS_FIELDS,
    TimeDashboardManager,
    TimeSettings,
    TimeSettingsManager,
)
from pyvergeos.resources.updates import (
    UpdatePackage,
    UpdatePackageManager,
    UpdateSettingsManager,
    UpdateSourceStatus,
    UpdateSourceStatusManager,
)
from pyvergeos.resources.users import User
from pyvergeos.resources.vm_imports import VmImport, VmImportManager
from pyvergeos.resources.vms import MACHINE_TYPES, VM, VMManager
from pyvergeos.resources.vmware import VmwareContainerManager
from pyvergeos.resources.vsan_queries import VSAN_QUERY_TYPES, VsanQueryManager
from pyvergeos.versions import version_at_least


def _version(client: VergeClient, version: str) -> None:
    assert client._connection is not None
    client._connection.os_version = version


def _fields(mock_session: MagicMock) -> str:
    params = mock_session.request.call_args.kwargs.get("params") or {}
    return str(params.get("fields") or "")


def _post_body(mock_session: MagicMock, fragment: str) -> dict[str, Any]:
    for call in mock_session.request.call_args_list:
        url = str(call.kwargs.get("url", ""))
        if call.kwargs.get("method") == "POST" and fragment in url:
            body = call.kwargs.get("json")
            assert isinstance(body, dict)
            return body
    raise AssertionError(f"no POST to {fragment}")


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("26.1.8", False),
        ("26.1", False),
        ("26.2", True),
        ("26.2.2.1", True),
        ("26.10.0", True),
        (None, False),
    ],
)
def test_version_at_least_26_2(version: str | None, expected: bool) -> None:
    """26.2 fields are included from 26.2 onward and left out before that."""
    assert version_at_least(version, 26, 2) is expected


class TestTime:
    """time_settings and time_dashboard."""

    def test_get_requests_ntp_and_ptp_columns(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "mode": "ntp"}
        settings = mock_client.time_settings.get()
        assert isinstance(settings, TimeSettings)
        fields = _fields(mock_session)
        for name in (
            "mode",
            "ntp_servers",
            "ntp_max_clocks",
            "ntp_min_clocks",
            "ntp_min_sane",
            "ptp_interface_network",
            "ptp_transport",
            "ptp_domain",
            "ptp_delay_mechanism",
            "ptp_hardware_timestamps",
            "ptp_priority1",
            "ptp_priority2",
            "ptp_sync_receipt_timeout",
            "ptp_announce_receipt_timeout",
        ):
            assert name in fields
        assert set(TIME_SETTINGS_FIELDS) <= set(fields.split(","))
        url = mock_session.request.call_args.kwargs["url"]
        assert url.endswith("/time_settings/1")

    def test_update_payload(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "mode": "ptp"},
            {"$key": 1, "mode": "ptp", "ptp_domain": 24},
        ]
        updated = mock_client.time_settings.update(
            mode="ptp",
            ptp_interface_network=3,
            ptp_transport="l2",
            ptp_domain=24,
            ptp_hardware_timestamps=True,
            ptp_priority1=128,
            ptp_sync_receipt_timeout=0,
        )
        assert updated.mode == "ptp"
        put = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put) == 1
        body = put[0].kwargs["json"]
        assert body == {
            "mode": "ptp",
            "ptp_interface_network": 3,
            "ptp_transport": "l2",
            "ptp_domain": 24,
            "ptp_hardware_timestamps": True,
            "ptp_priority1": 128,
            "ptp_sync_receipt_timeout": 0,
        }
        assert put[0].kwargs["url"].endswith("/time_settings/1")

    def test_dashboard_wraps_node_rows(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "mode": "ntp",
            "settings": {"mode": "ntp", "ntp_servers": "0.pool.ntp.org"},
            "nodes": [
                {"node": 1, "name": "node1", "synced": True, "source": "0.pool.ntp.org"},
                {"node": 2, "name": "node2", "status": "synced", "source": "10.0.0.1"},
            ],
            "alarms": [{"alarm_id": "abc"}],
        }
        dashboard = mock_client.time_dashboard.get()
        assert dashboard.mode == "ntp"
        assert len(dashboard.nodes) == 2
        assert dashboard.nodes[0].synced is True
        assert dashboard.nodes[0].source == "0.pool.ntp.org"
        assert dashboard.alarms[0]["alarm_id"] == "abc"
        assert mock_session.request.call_args.kwargs["url"].endswith("/time_dashboard")
        assert mock_session.request.call_args.kwargs.get("params") in (None, {})


class TestVMFields:
    """VM create, clone, and versioned columns."""

    def test_machine_types_include_q35_11(self) -> None:
        assert "pc-q35-10.1" in MACHINE_TYPES
        assert "pc-q35-10.2" in MACHINE_TYPES
        assert "pc-q35-11.0" in MACHINE_TYPES

    def test_cpu_types_include_qemu_11(self) -> None:
        for name in ("ClearwaterForest", "DiamondRapids", "SierraForest", "EPYC-Turin"):
            assert name in CPU_TYPES

    def test_create_omits_machine_type(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 7, "name": "vm"},
            {"$key": 7, "name": "vm"},
        ]
        mock_client.vms.create(name="vm")
        body = _post_body(mock_session, "/vms")
        assert "machine_type" not in body

    def test_create_sends_machine_type_when_chosen(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 7, "name": "vm"},
            {"$key": 7, "name": "vm", "machine_type": "pc-q35-11.0"},
        ]
        mock_client.vms.create(name="vm", machine_type="pc-q35-11.0")
        body = _post_body(mock_session, "/vms")
        assert body["machine_type"] == "pc-q35-11.0"

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_default_fields_follow_server_version(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        mock_client.vms.list()
        fields = _fields(mock_session)
        for name in ("bios_serial", "vgamem_mb"):
            assert (name in fields) is version.startswith("26.2")

    def test_clone_preserve_bios_serial(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"task": 1}
        vm = VM({"$key": 4, "name": "src"}, mock_client.vms)
        vm.clone(preserve_bios_serial=True)
        body = mock_session.request.call_args.kwargs["json"]
        assert body["action"] == "clone"
        assert body["params"]["preserve_bios_serial"] is True
        assert body["params"]["preserve_macs"] is False

    def test_clone_omits_preserve_bios_serial_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"task": 1}
        vm = VM({"$key": 4, "name": "src"}, mock_client.vms)
        vm.clone()
        body = mock_session.request.call_args.kwargs["json"]
        assert "preserve_bios_serial" not in body["params"]

    def test_properties(self, mock_client: VergeClient) -> None:
        vm = VM(
            {"$key": 1, "bios_serial": "ABC", "vgamem_mb": 64},
            VMManager(mock_client),
        )
        assert vm.bios_serial == "ABC"
        assert vm.vgamem_mb == 64


class TestImportsDrivesFiles:
    """Import, drive, and file columns."""

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.0"])
    def test_import_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        VmImportManager(mock_client).list()
        fields = _fields(mock_session)
        for name in ("preserve_bios_serial", "guest_agent_preinstalled", "replicate_tags"):
            assert (name in fields) is version.startswith("26.2")

    def test_import_create_payload(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": "abc", "name": "imported"},
            [{"$key": "abc", "name": "imported", "preserve_bios_serial": True}],
        ]
        created = VmImportManager(mock_client).create(
            name="imported",
            file=9,
            preserve_bios_serial=True,
            guest_agent_preinstalled=True,
            replicate_tags=True,
        )
        assert isinstance(created, VmImport)
        body = _post_body(mock_session, "/vm_imports")
        assert body["preserve_bios_serial"] is True
        assert body["guest_agent_preinstalled"] is True
        assert body["replicate_tags"] is True

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_drive_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        vm = VM({"$key": 1, "machine": 2}, mock_client.vms)
        DriveManager(mock_client, vm).list()
        fields = _fields(mock_session)
        for name in ("uuid", "is_primary"):
            assert (name in fields) is version.startswith("26.2")
        assert ("ms_2023_kek_applied" in fields) is True

    def test_drive_create_share_and_ovmf(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 8, "name": "efi"},
            {"$key": 8, "name": "efi", "machine": 2, "media": "efidisk"},
        ]
        vm = VM({"$key": 1, "machine": 2}, mock_client.vms)
        DriveManager(mock_client, vm).create(
            name="efi",
            media="efidisk",
            share=True,
            ovmf_code=15,
        )
        body = _post_body(mock_session, "/machine_drives")
        assert body["share"] is True
        assert body["ovmf_code"] == 15
        assert "disksize" not in body

    def test_file_type_fd_and_uuid_gating(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        assert FILE_TYPES["fd"] == "OVMF firmware"
        _version(mock_client, "26.1.8")
        mock_session.request.return_value.json.return_value = []
        FileManager(mock_client).list()
        assert "uuid" not in _fields(mock_session)
        _version(mock_client, "26.2.2.1")
        FileManager(mock_client).list()
        assert "uuid" in _fields(mock_session)


class TestMachineStatusAndNics:
    """Machine status columns and the 255 NIC allowance."""

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.1"])
    def test_status_fields(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = [{"$key": 1, "machine": 3}]
        MachineStatusManager(mock_client, 3).get()
        fields = _fields(mock_session)
        for name in ("agent_ip_list", "time_sync_status"):
            assert (name in fields) is version.startswith("26.2")

    def test_status_properties(self, mock_client: VergeClient) -> None:
        status = MachineStatus(
            {
                "$key": 1,
                "machine": 3,
                "agent_ip_list": "10.1.1.5, 10.1.1.6",
                "time_sync_status": "synced",
            },
            MachineStatusManager(mock_client, 3),
        )
        assert status.agent_ip_list == ["10.1.1.5", "10.1.1.6"]
        assert status.time_sync_status == "synced"

    def test_nic_limit_constant(self) -> None:
        assert MAX_NICS_PER_MACHINE == 255

    def test_nic_update_accepts_high_order(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "machine": 2, "orderid": 255},
            {"$key": 1, "machine": 2, "orderid": 255},
        ]
        vm = VM({"$key": 1, "machine": 2}, mock_client.vms)
        NICManager(mock_client, vm).update(1, orderid=255)
        put = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert put[0].kwargs["json"]["orderid"] == 255


class TestNetworks:
    """Network, bond, BGP, and Wake-on-LAN."""

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_network_fields(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        NetworkManager(mock_client).list()
        fields = _fields(mock_session)
        for name in (
            "dhcp_broadcast",
            "vlan_bond_mode",
            "vlan_bond_primary",
            "vlan_bond_miimon",
            "vlan_bond_updelay",
            "vlan_bond_downdelay",
            "vlan_bond_xmit_hash_policy",
        ):
            assert (name in fields) is version.startswith("26.2")

    def test_create_sends_dhcp_broadcast_only_when_set(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 4},
            {"$key": 4, "name": "edge", "dhcp_broadcast": True},
        ]
        NetworkManager(mock_client).create(
            name="edge", dhcp_broadcast=True, vlan_bond_mode="balance-slb"
        )
        body = _post_body(mock_session, "/vnets")
        assert body["dhcp_broadcast"] is True
        assert body["vlan_bond_mode"] == "balance-slb"

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_bond_primary_field(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        VnetBondInterfaceManager(mock_client, 4).list()
        assert ("primary" in _fields(mock_session)) is version.startswith("26.2")

    def test_bgp_config_fields_and_update(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        _version(mock_client, "26.2.2.1")
        network = Network({"$key": 6, "name": "edge"}, mock_client.networks)
        routing = NetworkRoutingManager(mock_client, network)
        mock_session.request.return_value.json.return_value = [
            {"$key": 2, "vnet": 6, "bgpd_enabled": True}
        ]
        config = routing.get_config()
        assert config is not None
        assert config.bgpd_enabled is True
        fields = _fields(mock_session)
        for name in VNET_BGP_26_2_FIELDS:
            assert name in fields

        _version(mock_client, "26.1.8")
        routing.get_config()
        fields_old = _fields(mock_session)
        for name in VNET_BGP_26_2_FIELDS:
            assert name not in fields_old

    def test_bgp_update_payload(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        network = Network({"$key": 6, "name": "edge"}, mock_client.networks)
        routing = NetworkRoutingManager(mock_client, network)
        mock_session.request.return_value.json.side_effect = [
            [],
            {"$key": 8, "vnet": 6},
            {"ok": True},
            [{"$key": 8, "vnet": 6, "console_rows": 40, "persisted_config": "hostname edge"}],
        ]
        updated = routing.update_config(
            console_rows=40,
            console_columns=120,
            persisted_config="hostname edge",
            bgpd_enabled=True,
            ospfd_enabled=False,
            eigrpd_enabled=False,
        )
        assert updated.console_rows == 40
        assert updated.persisted_config == "hostname edge"
        put = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert put[0].kwargs["json"] == {
            "console_rows": 40,
            "console_columns": 120,
            "persisted_config": "hostname edge",
            "bgpd_enabled": True,
            "ospfd_enabled": False,
            "eigrpd_enabled": False,
        }

    def test_wakeonlan_query_and_network_wrapper(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        assert "wakeonlan" in get_args(VNetQueryType)
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "vnet": 6,
            "query": "wakeonlan",
            "status": "complete",
            "result": "sent",
        }
        network = Network({"$key": 6, "name": "edge"}, mock_client.networks)
        result = network.wakeonlan("aa:bb:cc:dd:ee:ff")
        assert result.query_type == "wakeonlan"
        body = _post_body(mock_session, "/vnet_queries")
        assert body["query"] == "wakeonlan"
        assert body["vnet"] == 6
        assert body["params"] == {"mac": "aa:bb:cc:dd:ee:ff"}


class TestAlarmsUpdatesVMware:
    """Alarms, package uninstall, and VixDiskLib."""

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_alarm_sub_owner_type_field(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        AlarmManager(mock_client).list(sub_owner_type="VirtualSwitchPort")
        fields = _fields(mock_session)
        assert ("sub_owner_type" in fields) is version.startswith("26.2")
        filt = mock_session.request.call_args.kwargs["params"]["filter"]
        assert "sub_owner_type eq 'vnet_wires'" in filt

    def test_alarm_display(self, mock_client: VergeClient) -> None:
        alarm = Alarm(
            {"$key": 1, "sub_owner_type": "vnet_wires", "level": "warning"},
            AlarmManager(mock_client),
        )
        assert alarm.sub_owner_type == "vnet_wires"
        assert alarm.sub_owner_type_display == "Virtual Switch Port"

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_package_dependencies_field(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = []
        UpdatePackageManager(mock_client).list()
        assert ("dependencies" in _fields(mock_session)) is version.startswith("26.2")

    def test_dependencies_property(self, mock_client: VergeClient) -> None:
        package = UpdatePackage(
            {"$key": "ai", "name": "ai", "dependencies": ["vergeos", "help"]},
            UpdatePackageManager(mock_client),
        )
        assert package.dependencies == ["vergeos", "help"]

    @pytest.mark.parametrize("version", ["26.1.8", "26.2.2.1"])
    def test_restart_pending_packages_field(
        self, mock_client: VergeClient, mock_session: MagicMock, version: str
    ) -> None:
        _version(mock_client, version)
        mock_session.request.return_value.json.return_value = {"$key": 1, "source": 1}
        UpdateSettingsManager(mock_client).get()
        assert ("restart_pending_packages" in _fields(mock_session)) is version.startswith("26.2")

    def test_uninstall_payload(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "source": 4},
            {"task": 12},
        ]
        result = UpdateSettingsManager(mock_client).uninstall("private-ai")
        assert result == {"task": 12}
        body = _post_body(mock_session, "/update_actions")
        assert body == {"source": 4, "action": "uninstall", "installed_package": "private-ai"}

    def test_uninstalling_is_busy(self, mock_client: VergeClient) -> None:
        status = UpdateSourceStatus(
            {"$key": 1, "status": "uninstalling"},
            UpdateSourceStatusManager(mock_client),
        )
        assert status.is_uninstalling is True
        assert status.is_busy is True

    def test_install_vixdisklib(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {"task": 3}
        VmwareContainerManager(mock_client).install_vixdisklib(5, "VMware-vix-disklib.tar.gz")
        call = mock_session.request.call_args
        assert call.kwargs["method"] == "PUT"
        assert "vmware_containers/5" in call.kwargs["url"]
        assert "action=install_vixdisklib" in call.kwargs["url"]
        assert call.kwargs["json"] == {"filename": "VMware-vix-disklib.tar.gz"}


class TestCompatibility:
    """Idle sync status, computed physical access, and findinode."""

    def test_site_sync_status_defaults_to_idle(self) -> None:
        outgoing = SiteSyncOutgoing({"$key": 1}, MagicMock())
        incoming = SiteSyncIncoming({"$key": 1}, MagicMock())
        assert outgoing.status == "idle"
        assert incoming.status == "idle"
        assert outgoing.is_idle is True
        older = SiteSyncOutgoing({"$key": 1, "status": "offline"}, MagicMock())
        assert older.status == "offline"
        assert older.is_idle is False

    def test_physical_access_is_documented_as_computed(self) -> None:
        text = User.physical_access.__doc__ or ""
        assert "Super Users" in text
        assert "administrator flag" in text
        assert "administrator privileges" not in text.lower()

    def test_findinode_is_not_a_public_query(self) -> None:
        assert "findinode" not in VSAN_QUERY_TYPES
        assert not hasattr(VsanQueryManager, "findinode")


def test_client_exposes_new_managers(mock_client: VergeClient) -> None:
    """The new resources are on the client."""
    assert isinstance(mock_client.time_settings, TimeSettingsManager)
    assert isinstance(mock_client.time_dashboard, TimeDashboardManager)
    assert isinstance(mock_client.vmware_containers, VmwareContainerManager)
    assert isinstance(mock_client.vnet_bond_interfaces, VnetBondInterfaceManager)
