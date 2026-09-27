"""Scoped managers must refuse another parent's row on by-key calls (#168, #188)."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.vms import VM

OWN_MACHINE = 200
OTHER_MACHINE = 60
OWN_VM_KEY = 100
FOREIGN_KEY = 2
FOREIGN_OWNER = "vms/42"


def _operation_calls(mock_session: MagicMock) -> list[MagicMock]:
    """Requests other than the connection check against /system."""
    return [
        call
        for call in mock_session.request.call_args_list
        if not str(call.kwargs.get("url", "")).rstrip("/").endswith("/system")
    ]


def _assert_only_scope_read(
    mock_session: MagicMock,
    endpoint: str,
    key: int,
    *,
    scope_field: str = "machine",
) -> None:
    """The call fetched the row and sent no write."""
    calls = _operation_calls(mock_session)
    assert len(calls) == 1
    assert calls[0].kwargs.get("method") == "GET"
    assert f"/{endpoint}/{key}" in calls[0].kwargs.get("url", "")
    fields = str(calls[0].kwargs.get("params", {}).get("fields", ""))
    assert scope_field in fields.split(",")
    writes = [
        call.kwargs.get("method")
        for call in mock_session.request.call_args_list
        if call.kwargs.get("method") in {"POST", "PUT", "DELETE", "PATCH"}
    ]
    assert writes == []


@pytest.fixture
def vm(mock_client: VergeClient) -> VM:
    """Stopped VM. In-place restore of another VM is the damaging case."""
    return VM(
        {"$key": 100, "name": "vm-a", "machine": OWN_MACHINE, "running": False},
        mock_client.vms,
    )


def _foreign_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "$key": FOREIGN_KEY,
        "name": "other-vm",
        "machine": OTHER_MACHINE,
    }
    row.update(extra)
    return row


class TestSnapshotMachineScope:
    """vm.snapshots must not touch a snapshot owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.snapshots.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Omitting machine from fields must not skip the scope check."""
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.get(FOREIGN_KEY, fields="$key,name")

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_get_accepts_string_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "own",
            "machine": str(OWN_MACHINE),
        }

        snapshot = vm.snapshots.get(1)

        assert snapshot.key == 1

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.update(FOREIGN_KEY, description="nope")

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_restore_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """In-place restore must not revert the VM that owns the snapshot."""
        mock_session.request.return_value.json.return_value = _foreign_row(snap_machine=999)

        with patch("time.sleep"), pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.restore(FOREIGN_KEY, replace_original=True)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)


class TestDriveMachineScope:
    """vm.drives must not touch a drive owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.drives.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.get(FOREIGN_KEY, fields=["$key", "name"])

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.update(FOREIGN_KEY, description="written on the wrong drive")

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)


class TestNICMachineScope:
    """vm.nics must not touch a NIC owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.nics.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.get(FOREIGN_KEY, fields="$key,name")

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.update(FOREIGN_KEY, description="written on the wrong nic")

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)


def _foreign_cloudinit(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "$key": FOREIGN_KEY,
        "name": "/user-data",
        "owner": FOREIGN_OWNER,
    }
    row.update(extra)
    return row


class TestDeviceMachineScope:
    """vm.devices must not touch a device owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row(type="tpm")

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.devices.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_devices", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Omitting machine from fields must not skip the scope check."""
        mock_session.request.return_value.json.return_value = _foreign_row(type="tpm")

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.devices.get(FOREIGN_KEY, fields="$key,name")

        _assert_only_scope_read(mock_session, "machine_devices", FOREIGN_KEY)

    def test_get_accepts_string_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "qa-tpm",
            "type": "tpm",
            "machine": str(OWN_MACHINE),
        }

        device = vm.devices.get(1)

        assert device.key == 1

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row(type="tpm")

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.devices.update(FOREIGN_KEY, enabled=False)

        _assert_only_scope_read(mock_session, "machine_devices", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row(type="tpm")

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.devices.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_devices", FOREIGN_KEY)


class TestCloudInitFileOwnerScope:
    """vm.cloudinit_files must not touch a file owned by another VM."""

    def test_get_refuses_other_vm(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_cloudinit()

        with pytest.raises(NotFoundError, match="does not belong to VM 100"):
            vm.cloudinit_files.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "cloudinit_files", FOREIGN_KEY, scope_field="owner")

    def test_get_narrowed_fields_still_requests_owner(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Omitting owner from fields must not skip the scope check."""
        mock_session.request.return_value.json.return_value = _foreign_cloudinit()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.cloudinit_files.get(FOREIGN_KEY, fields=["$key", "name"])

        _assert_only_scope_read(mock_session, "cloudinit_files", FOREIGN_KEY, scope_field="owner")

    def test_get_accepts_own_owner(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": f"vms/{OWN_VM_KEY}",
        }

        cloudinit_file = vm.cloudinit_files.get(1)

        assert cloudinit_file.key == 1
        assert cloudinit_file.owner == f"vms/{vm.key}"

    def test_get_content_refuses_other_vm(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """get_content does not go through get, so it must check scope itself."""
        mock_session.request.return_value.json.return_value = _foreign_cloudinit(
            contents="#cloud-config\nhostname: b\n"
        )
        mock_session.request.return_value.content = b"#cloud-config\nhostname: b\n"

        with pytest.raises(NotFoundError, match="does not belong to VM 100"):
            vm.cloudinit_files.get_content(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "cloudinit_files", FOREIGN_KEY, scope_field="owner")
        downloads = [
            call
            for call in mock_session.request.call_args_list
            if (call.kwargs.get("params") or {}).get("download") == 1
        ]
        assert downloads == []

    def test_get_content_returns_own_file(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "/user-data",
            "owner": f"vms/{OWN_VM_KEY}",
        }
        mock_session.request.return_value.content = b"#cloud-config\nhostname: a\n"
        mock_session.request.return_value.status_code = 200

        content = vm.cloudinit_files.get_content(1)

        assert content == "#cloud-config\nhostname: a\n"
        downloads = [
            call
            for call in _operation_calls(mock_session)
            if (call.kwargs.get("params") or {}).get("download") == 1
        ]
        assert len(downloads) == 1

    def test_update_refuses_other_vm(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_cloudinit()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.cloudinit_files.update(FOREIGN_KEY, contents="#cloud-config\nhostname: crossed\n")

        _assert_only_scope_read(mock_session, "cloudinit_files", FOREIGN_KEY, scope_field="owner")

    def test_delete_refuses_other_vm(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_cloudinit()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.cloudinit_files.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "cloudinit_files", FOREIGN_KEY, scope_field="owner")


def _foreign_parent_value(expected: object) -> object:
    """A value that cannot compare equal to ``expected``."""
    if isinstance(expected, bool):
        return not expected
    if isinstance(expected, int):
        return expected + 1000
    if isinstance(expected, str) and "/" in expected:
        table, _, _rest = expected.partition("/")
        return f"{table}/999999"
    if isinstance(expected, str):
        return f"{expected}-other"
    return "other"


def _handed_managers(parent: object) -> list[tuple[str, object]]:
    """Resource managers this parent object hands out as properties."""
    from pyvergeos.resources.base import ResourceManager

    found: list[tuple[str, object]] = []
    seen: set[str] = set()
    for cls in type(parent).__mro__:
        for name, attr in cls.__dict__.items():
            if name in seen or not isinstance(attr, property) or attr.fget is None:
                continue
            seen.add(name)
            returned = attr.fget.__annotations__.get("return", "")
            if not str(returned).endswith("Manager"):
                continue
            value = getattr(parent, name)
            if isinstance(value, ResourceManager):
                found.append((name, value))
    return found


def _takes_key(method: object) -> bool:
    params = [
        param
        for param in inspect.signature(method).parameters.values()  # type: ignore[arg-type]
        if param.name != "self"
    ]
    return bool(params) and params[0].name == "key"


def _call_with_key(method: object, key: int) -> None:
    """Call ``method(key)``, filling required arguments the scope check ignores."""
    signature = inspect.signature(method)  # type: ignore[arg-type]
    kwargs: dict[str, object] = {}
    var_keyword = False
    for param in list(signature.parameters.values())[1:]:
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            var_keyword = True
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.POSITIONAL_ONLY,
        ):
            continue
        if param.annotation in (bool, "bool"):
            kwargs[param.name] = False
        elif param.annotation in (int, "int"):
            kwargs[param.name] = 0
        else:
            kwargs[param.name] = "x"
    if var_keyword and not kwargs:
        kwargs["description"] = "crossed"
    method(key, **kwargs)  # type: ignore[operator]


def _assert_refused(mock_session: MagicMock, manager: object, key: int) -> None:
    """The call raised a scope error and sent no write."""
    from pyvergeos.resources.base import ResourceManager

    assert isinstance(manager, ResourceManager)
    calls = _operation_calls(mock_session)
    writes = [
        call.kwargs.get("method")
        for call in calls
        if call.kwargs.get("method") in {"POST", "PUT", "DELETE", "PATCH"}
    ]
    assert writes == []
    columns = [column for column, _expected in manager._scope_bindings()]
    for call in calls:
        if call.kwargs.get("method") != "GET":
            continue
        url = str(call.kwargs.get("url", ""))
        if f"/{manager._endpoint}/{key}" not in url:
            continue
        fields = str((call.kwargs.get("params") or {}).get("fields", ""))
        # An unprojected get returns own-columns, including the parent column.
        if not fields:
            continue
        for column in columns:
            assert column in fields.split(","), url


def _scoped_parents(mock_client: VergeClient, vm: VM) -> list[tuple[str, object]]:
    """Parents that hand out a scoped manager. Names stay off Core and DMZ."""
    from pyvergeos.resources.dns import DNSZone, DNSZoneManager
    from pyvergeos.resources.dns_views import DNSView, DNSViewManager
    from pyvergeos.resources.ipsec import IPSecConnection, IPSecConnectionManager
    from pyvergeos.resources.nas_services import NASService
    from pyvergeos.resources.nas_volumes import NASVolume
    from pyvergeos.resources.networks import Network
    from pyvergeos.resources.oidc_applications import OidcApplication
    from pyvergeos.resources.resource_groups import ResourceGroup
    from pyvergeos.resources.task_schedules import TaskSchedule
    from pyvergeos.resources.tasks import Task
    from pyvergeos.resources.tenant_manager import Tenant
    from pyvergeos.resources.vnet_proxy import VnetProxy, VnetProxyManager
    from pyvergeos.resources.wireguard import WireGuardInterface, WireGuardManager

    network = Network({"$key": 3, "name": "Internal"}, mock_client.networks)
    tenant = Tenant({"$key": 5, "name": "tenant-a"}, mock_client.tenants)
    volume = NASVolume({"$key": "a" * 40, "name": "share"}, mock_client.nas_volumes)
    service = NASService({"$key": 7, "name": "nas"}, mock_client.nas_services)
    group = ResourceGroup(
        {"uuid": "11111111-1111-1111-1111-111111111111", "name": "gpus"},
        mock_client.resource_groups,
    )
    task = Task({"$key": 9, "name": "job"}, mock_client.tasks)
    schedule = TaskSchedule({"$key": 11, "name": "nightly"}, mock_client.task_schedules)
    app = OidcApplication({"$key": 13, "name": "portal"}, mock_client.oidc_applications)
    wireguard = WireGuardInterface(
        {"$key": 15, "name": "wg0", "vnet": network.key},
        WireGuardManager(mock_client, network),
    )
    zone = DNSZone(
        {"$key": 17, "domain": "example.com", "view": 4},
        DNSZoneManager(mock_client, network=network),
    )
    view = DNSView(
        {"$key": 4, "name": "default", "vnet": network.key},
        DNSViewManager(mock_client, network),
    )
    connection = IPSecConnection(
        {"$key": 19, "name": "hq", "vnet": network.key},
        IPSecConnectionManager(mock_client, network),
    )
    proxy = VnetProxy(
        {"$key": 21, "vnet": network.key, "listen_address": "0.0.0.0"},
        VnetProxyManager(mock_client, network),
    )
    return [
        ("Network", network),
        ("Tenant", tenant),
        ("NASVolume", volume),
        ("NASService", service),
        ("ResourceGroup", group),
        ("Task", task),
        ("TaskSchedule", schedule),
        ("OidcApplication", app),
        ("VM", vm),
        ("WireGuardInterface", wireguard),
        ("DNSZone", zone),
        ("DNSView", view),
        ("IPSecConnection", connection),
        ("VnetProxy", proxy),
    ]


# Managers the issue names, plus the VM managers that already checked scope.
_REQUIRED_MANAGERS = {
    "Network.rules",
    "Network.aliases",
    "Network.hosts",
    "Network.wireguard",
    "Network.dns_zones",
    "Network.ipsec",
    "Tenant.network_blocks",
    "Tenant.external_ips",
    "Tenant.nodes",
    "Tenant.storage",
    "Tenant.snapshots",
    "Tenant.l2_networks",
    "NASVolume.antivirus",
    "NASService.antivirus",
    "ResourceGroup.rules",
    "Task.triggers",
    "OidcApplication.allowed_users",
    "OidcApplication.allowed_groups",
    "WireGuardInterface.peers",
    "DNSZone.records",
    "IPSecConnection.policies",
    "VM.drives",
    "VM.nics",
    "VM.snapshots",
    "VM.devices",
    "VM.cloudinit_files",
}


def test_parent_handed_managers_refuse_other_parents(
    mock_client: VergeClient, mock_session: MagicMock, vm: VM
) -> None:
    """Every manager a parent hands out must refuse another parent's key (#188)."""
    failures: list[str] = []
    seen: set[str] = set()

    for label, parent in _scoped_parents(mock_client, vm):
        handed = _handed_managers(parent)
        if not handed:
            failures.append(f"{label} handed no managers")
            continue
        for name, manager in handed:
            ident = f"{label}.{name}"
            seen.add(ident)
            bindings = manager._scope_bindings()  # type: ignore[attr-defined]
            if not bindings:
                failures.append(f"{ident} has no scope bindings")
                continue
            row: dict[str, object] = {"$key": FOREIGN_KEY, "name": "other-parent"}
            for column, expected in bindings:
                row[column] = _foreign_parent_value(expected)
            for op_name in ("get", "update", "delete"):
                method = getattr(manager, op_name)
                if not _takes_key(method):
                    continue
                mock_session.request.reset_mock()
                mock_session.request.return_value.json.return_value = row
                try:
                    _call_with_key(method, FOREIGN_KEY)
                except NotFoundError as exc:
                    if "does not belong" not in str(exc):
                        failures.append(f"{ident}.{op_name}: {exc}")
                        continue
                except Exception as exc:
                    failures.append(f"{ident}.{op_name}: {type(exc).__name__}: {exc}")
                    continue
                else:
                    failures.append(f"{ident}.{op_name} returned a foreign row")
                    continue
                try:
                    _assert_refused(mock_session, manager, FOREIGN_KEY)
                except AssertionError as exc:
                    failures.append(f"{ident}.{op_name}: {exc}")

    missing = _REQUIRED_MANAGERS - seen
    if missing:
        failures.append("missing managers: " + ", ".join(sorted(missing)))
    assert not failures, "\n".join(failures)
