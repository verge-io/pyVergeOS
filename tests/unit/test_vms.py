"""Unit tests for VM operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.vms import VM, VMManager


def _http(status: int, payload: dict[str, Any] | None) -> MagicMock:
    """Build a mock requests response for ``VergeClient._handle_response``."""
    response = MagicMock()
    response.status_code = status
    if payload is None:
        response.text = ""
        response.json.return_value = None
    else:
        response.text = "{}"
        response.json.return_value = payload
    return response


class TestVMManager:
    """Unit tests for VMManager."""

    def test_list_vms(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing VMs."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "test-vm-1",
                "status": "running",
                "running": True,
                "is_snapshot": False,
            },
            {
                "$key": 2,
                "name": "test-vm-2",
                "status": "stopped",
                "running": False,
                "is_snapshot": False,
            },
        ]

        vms = mock_client.vms.list()

        assert len(vms) == 2
        assert vms[0].name == "test-vm-1"
        assert vms[1].name == "test-vm-2"

    def test_list_vms_excludes_snapshots_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() adds filter to exclude snapshots."""
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list()

        # Check that the filter includes is_snapshot eq false
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "is_snapshot eq false" in params.get("filter", "")

    def test_list_vms_include_snapshots(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that include_snapshots=True doesn't add the filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list(include_snapshots=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        # Should not have is_snapshot filter when include_snapshots=True
        filter_value = params.get("filter", "")
        assert "is_snapshot" not in filter_value or filter_value is None

    def test_list_vms_name_kwarg_is_merged_with_snapshot_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Shorthand kwargs must merge with the snapshot filter (issue #96).

        Previously the always-present snapshot filter caused every
        filter kwarg to be silently dropped, so vms.list(name=X)
        returned every VM.
        """
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list(name="does-not-exist")

        params = mock_session.request.call_args.kwargs.get("params", {})
        filter_value = params.get("filter", "")
        assert "is_snapshot eq false" in filter_value
        assert "name eq 'does-not-exist'" in filter_value

    def test_list_vms_all_none_kwargs_raise(self, mock_client: VergeClient) -> None:
        """All-None filter kwargs must not widen to a full table scan (issue #96)."""
        with pytest.raises(ValueError, match="empty filter"):
            mock_client.vms.list(name=None)

    def test_get_vm_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a VM by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "test-vm",
            "status": "running",
        }

        vm = mock_client.vms.get(123)

        assert vm.key == 123
        assert vm.name == "test-vm"

    def test_get_vm_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a VM by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 456,
                "name": "my-vm",
                "status": "stopped",
            }
        ]

        vm = mock_client.vms.get(name="my-vm")

        assert vm.name == "my-vm"
        assert vm.key == 456

    def test_get_vm_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that NotFoundError is raised when VM not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.vms.get(name="nonexistent")

    def test_get_vm_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that ValueError is raised when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.vms.get()

    def test_create_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a VM."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 789, "name": "new-vm", "ram": 2048, "cpu_cores": 2},  # POST response
            {"$key": 789, "name": "new-vm", "ram": 2048, "cpu_cores": 2},  # GET response
        ]

        vm = mock_client.vms.create(
            name="new-vm",
            ram=2048,
            cpu_cores=2,
            os_family="linux",
        )

        assert vm.name == "new-vm"
        assert vm.key == 789

    def test_create_vm_normalizes_ram(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that RAM is normalized to 256MB increments."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "test", "ram": 2304},  # POST response
            {"$key": 1, "name": "test", "ram": 2304},  # GET response
        ]

        mock_client.vms.create(name="test", ram=2100)

        # Find the POST call to vms endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vms" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["ram"] == 2304  # Rounded up to nearest 256

    def test_update_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "updated-vm",
            "description": "New description",
        }

        vm = mock_client.vms.update(123, description="New description")

        assert vm.get("description") == "New description"
        assert mock_session.request.call_args.kwargs["json"] == {"description": "New description"}

    def test_delete_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a VM."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.vms.delete(123)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "vms/123" in call_args.kwargs["url"]

    @pytest.mark.parametrize("datasource", ["", "none"])
    @pytest.mark.parametrize("operation", ["update", "save", "setter"])
    def test_disable_cloudinit(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        datasource: str,
        operation: str,
    ) -> None:
        """All VM mutation paths send the API's 'none' disable value."""
        vm = VM({"$key": 123, "cloudinit_datasource": "nocloud"}, mock_client.vms)
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "cloudinit_datasource": "none",
        }

        if operation == "update":
            mock_client.vms.update(vm.key, cloudinit_datasource=datasource)
        elif operation == "save":
            vm.save(cloudinit_datasource=datasource)
        else:
            vm.set_cloudinit_datasource(datasource)
            assert vm["cloudinit_datasource"] == "none"

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "PUT"
        assert call_args.kwargs["url"].endswith("/vms/123")
        assert call_args.kwargs["json"] == {"cloudinit_datasource": "none"}

    @pytest.mark.parametrize("datasource", ["", "none", "None"])
    def test_create_vm_with_cloudinit_disabled(
        self, mock_client: VergeClient, mock_session: MagicMock, datasource: str
    ) -> None:
        """Explicit disabling must not auto-enable delivery when files are supplied."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "cloudinit_datasource": "none"},
        ]

        vm = mock_client.vms.create(name="cloud-vm", cloudinit_datasource=datasource, cloud_init={})

        post_call = next(
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        )
        assert post_call.kwargs["json"]["cloudinit_datasource"] == "none"
        assert vm["cloudinit_datasource"] == "none"

    def test_create_vm_with_cloudinit_datasource(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a VM with cloud-init datasource enabled."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "cloud-vm", "ram": 1024},  # POST response
            {"$key": 1, "name": "cloud-vm", "ram": 1024},  # GET response
        ]

        mock_client.vms.create(name="cloud-vm", cloudinit_datasource="ConfigDrive")

        # Find the POST call to vms endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vms" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("cloudinit_datasource") == "config_drive_v2"

    def test_create_vm_with_cloudinit_datasource_nocloud(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a VM with NoCloud datasource."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "cloud-vm", "ram": 1024},
            {"$key": 1, "name": "cloud-vm", "ram": 1024},
        ]

        mock_client.vms.create(name="cloud-vm", cloudinit_datasource="NoCloud")

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vms" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("cloudinit_datasource") == "nocloud"

    def test_create_vm_with_cloud_init_string(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a VM with cloud_init as a string creates user-data file."""
        # Setup mock responses: VM create, VM get, cloud-init file create, file get
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "cloud-vm", "ram": 1024},  # POST vms
            {"$key": 100, "name": "cloud-vm", "ram": 1024},  # GET vms/100
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},  # POST cloudinit_files
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},  # GET cloudinit_files/1
        ]

        user_data = "#cloud-config\npackages:\n  - nginx"
        mock_client.vms.create(name="cloud-vm", cloud_init=user_data)

        # Find POST calls
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]

        # Should have VM create and cloud-init file create
        assert len(post_calls) == 2

        # First POST is VM creation with ConfigDrive enabled
        vm_body = post_calls[0].kwargs.get("json", {})
        assert vm_body.get("cloudinit_datasource") == "config_drive_v2"

        # Second POST is cloud-init file creation
        file_body = post_calls[1].kwargs.get("json", {})
        assert file_body.get("name") == "/user-data"
        assert file_body.get("owner") == "vms/100"
        assert file_body.get("contents") == user_data

    def test_create_vm_with_cloud_init_dict(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a VM with cloud_init as a dict creates multiple files."""
        # Setup mock responses for VM and 2 cloud-init files
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "cloud-vm", "ram": 1024},  # POST vms
            {"$key": 100, "name": "cloud-vm", "ram": 1024},  # GET vms/100
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},  # POST file 1
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},  # GET file 1
            {"$key": 2, "name": "/meta-data", "owner": "vms/100"},  # POST file 2
            {"$key": 2, "name": "/meta-data", "owner": "vms/100"},  # GET file 2
        ]

        cloud_init = {
            "/user-data": "#cloud-config\npackages:\n  - nginx",
            "/meta-data": "instance-id: test-1\nlocal-hostname: cloud-vm",
        }
        mock_client.vms.create(name="cloud-vm", cloud_init=cloud_init)

        # Find POST calls to cloudinit_files
        cloudinit_posts = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "cloudinit_files" in call.kwargs.get("url", "")
        ]

        assert len(cloudinit_posts) == 2

    def test_create_vm_with_cloud_init_list(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a VM with cloud_init as a list with render options."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "cloud-vm", "ram": 1024},
            {"$key": 100, "name": "cloud-vm", "ram": 1024},
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
        ]

        cloud_init = [
            {"name": "/user-data", "contents": "#cloud-config", "render": "Jinja2"},
        ]
        mock_client.vms.create(name="cloud-vm", cloud_init=cloud_init)

        # Find POST to cloudinit_files
        cloudinit_posts = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "cloudinit_files" in call.kwargs.get("url", "")
        ]

        assert len(cloudinit_posts) == 1
        body = cloudinit_posts[0].kwargs.get("json", {})
        assert body.get("render") == "jinja2"

    def test_create_vm_with_invalid_cloudinit_datasource(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that invalid cloudinit_datasource raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cloudinit_datasource"):
            mock_client.vms.create(name="test", cloudinit_datasource="InvalidType")

    def test_create_vm_cloud_init_without_explicit_datasource(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that providing cloud_init auto-enables ConfigDrive datasource."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "cloud-vm", "ram": 1024},
            {"$key": 100, "name": "cloud-vm", "ram": 1024},
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
            {"$key": 1, "name": "/user-data", "owner": "vms/100"},
        ]

        # Don't explicitly set cloudinit_datasource, but provide cloud_init
        mock_client.vms.create(name="cloud-vm", cloud_init="#cloud-config")

        # Find the VM creation POST call
        vm_post = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "/vms" in call.kwargs.get("url", "")
            and "cloudinit_files" not in call.kwargs.get("url", "")
        ]

        assert len(vm_post) == 1
        body = vm_post[0].kwargs.get("json", {})
        # Should have auto-enabled ConfigDrive
        assert body.get("cloudinit_datasource") == "config_drive_v2"


class TestVM:
    """Unit tests for VM object."""

    @pytest.fixture
    def vm_data(self) -> dict[str, Any]:
        """Sample VM data."""
        return {
            "$key": 100,
            "name": "test-vm",
            "status": "running",
            "running": True,
            "is_snapshot": False,
            "node_name": "node1",
            "cluster_name": "cluster1",
            "machine": 200,
            "ram": 4096,
            "cpu_cores": 4,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> VMManager:
        """Create a mock VM manager."""
        return mock_client.vms

    def test_vm_properties(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test VM property accessors."""
        vm = VM(vm_data, mock_manager)

        assert vm.key == 100
        assert vm.name == "test-vm"
        assert vm.status == "running"
        assert vm.is_running is True
        assert vm.is_snapshot is False
        assert vm.node_name == "node1"
        assert vm.cluster_name == "cluster1"

    def test_vm_is_running_false(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test is_running when VM is stopped."""
        vm_data["running"] = False
        vm = VM(vm_data, mock_manager)

        assert vm.is_running is False

    def test_vm_is_snapshot_true(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test is_snapshot property."""
        vm_data["is_snapshot"] = True
        vm = VM(vm_data, mock_manager)

        assert vm.is_snapshot is True

    def test_power_on(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test powering on a VM."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_on()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweron"
        assert body["vm"] == 100

    def test_power_on_with_preferred_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test powering on a VM with preferred node."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_on(preferred_node=5)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["preferred_node"] == 5

    def test_power_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that powering on a snapshot raises ValueError."""
        vm_data["is_snapshot"] = True
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValueError, match="Cannot power on a snapshot"):
            vm.power_on()

    def test_power_off_graceful(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test graceful power off."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_off()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweroff"

    def test_power_off_force(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test forced power off."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_off(force=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "kill"

    def test_reset(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test VM reset."""
        vm = VM(vm_data, mock_client.vms)

        vm.reset()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_guest_reboot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test guest reboot sends graceful reset."""
        vm = VM(vm_data, mock_client.vms)

        vm.guest_reboot()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"
        assert body["params"] == {"graceful": True}

    def test_guest_shutdown(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test guest shutdown sends ACPI poweroff."""
        vm = VM(vm_data, mock_client.vms)

        vm.guest_shutdown()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweroff"

    def test_clone(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test cloning a VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 101,
            "name": "test-vm-clone",
        }

        vm = VM(vm_data, mock_client.vms)
        vm.clone(name="test-vm-clone", preserve_macs=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["params"]["name"] == "test-vm-clone"
        assert body["params"]["preserve_macs"] is True

    def test_move(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test moving a VM."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        vm = VM(vm_data, mock_client.vms)
        vm.move(node=5, cluster=2)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "move"
        assert body["params"]["node"] == 5
        assert body["params"]["cluster"] == 2

    def test_get_console_info(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test getting console info."""
        mock_session.request.return_value.json.return_value = {
            "name": "test-vm",
            "console": "vnc",
            "host": "192.168.1.100",
            "port": 5900,
        }

        vm = VM(vm_data, mock_client.vms)
        console = vm.get_console_info()

        assert console["console_type"] == "vnc"
        assert console["host"] == "192.168.1.100"
        assert console["port"] == 5900
        assert console["url"] == "vnc://192.168.1.100:5900"
        assert console["is_available"] is True

    def test_get_console_info_not_available(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test console info when not available."""
        mock_session.request.return_value.json.return_value = {
            "name": "test-vm",
            "console": "vnc",
            "host": None,
            "port": None,
        }

        vm = VM(vm_data, mock_client.vms)
        console = vm.get_console_info()

        assert console["is_available"] is False
        assert console["url"] is None

    def test_drives_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that drives property returns DriveManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.drives import DriveManager

        assert isinstance(vm.drives, DriveManager)
        # Should be same instance on subsequent access
        assert vm.drives is vm.drives

    def test_nics_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that nics property returns NICManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.nics import NICManager

        assert isinstance(vm.nics, NICManager)
        assert vm.nics is vm.nics

    def test_snapshots_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that snapshots property returns VMSnapshotManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.snapshots import VMSnapshotManager

        assert isinstance(vm.snapshots, VMSnapshotManager)
        assert vm.snapshots is vm.snapshots


class TestVMListHelpers:
    """Test VM list helper methods."""

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_running method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "vm1", "running": True, "is_snapshot": False},
            {"$key": 2, "name": "vm2", "running": False, "is_snapshot": False},
            {"$key": 3, "name": "vm3", "running": True, "is_snapshot": False},
        ]

        running = mock_client.vms.list_running()

        assert len(running) == 2
        assert all(vm.is_running for vm in running)

    def test_list_stopped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_stopped method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "vm1", "running": True, "is_snapshot": False},
            {"$key": 2, "name": "vm2", "running": False, "is_snapshot": False},
            {"$key": 3, "name": "vm3", "running": False, "is_snapshot": False},
        ]

        stopped = mock_client.vms.list_stopped()

        assert len(stopped) == 2
        assert all(not vm.is_running for vm in stopped)


class TestVMEnhancedActions:
    """Tests for enhanced VM actions (migrate, hibernate, changecd, restore, hotplug, tags)."""

    @pytest.fixture
    def vm_data(self) -> dict[str, Any]:
        """Sample VM data."""
        return {
            "$key": 100,
            "name": "test-vm",
            "status": "running",
            "running": True,
            "is_snapshot": False,
            "machine": 200,
        }

    def test_migrate_auto(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test live migration with auto node selection."""
        mock_session.request.return_value.json.return_value = {"task": 123}
        vm = VM(vm_data, mock_client.vms)

        result = vm.migrate()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "migrate"
        assert body["vm"] == 100
        assert "params" not in body  # No preferred_node specified
        assert result == {"task": 123}

    def test_migrate_preferred_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test live migration to a specific node."""
        mock_session.request.return_value.json.return_value = {"task": 456}
        vm = VM(vm_data, mock_client.vms)

        result = vm.migrate(preferred_node=5)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "migrate"
        assert body["params"]["preferred_node"] == 5
        assert result == {"task": 456}

    def test_hibernate(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test hibernating a VM."""
        mock_session.request.return_value.json.return_value = {"task": 789}
        vm = VM(vm_data, mock_client.vms)

        result = vm.hibernate()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "hibernate"
        assert body["vm"] == 100
        assert result == {"task": 789}

    def test_restore_overwrite(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test restoring VM from snapshot (overwrite current)."""
        mock_session.request.return_value.json.return_value = {"task": 333}
        vm = VM(vm_data, mock_client.vms)

        result = vm.restore(snapshot=50)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "restore"
        assert body["params"]["snapshot"] == 50
        assert body["params"]["preserve_macs"] is False
        assert "name" not in body["params"]
        assert result == {"task": 333}

    def test_restore_to_clone(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test restoring VM from snapshot to a new clone."""
        mock_session.request.return_value.json.return_value = {"task": 444}
        vm = VM(vm_data, mock_client.vms)

        result = vm.restore(snapshot=50, name="restored-vm", preserve_macs=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "restore"
        assert body["params"]["snapshot"] == 50
        assert body["params"]["name"] == "restored-vm"
        assert body["params"]["preserve_macs"] is True
        assert result == {"task": 444}

    def test_hotplug_drive(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Hotplug creates the drive, then posts its key as device."""
        drive_key = 77
        size = 10 * 1024**3
        # create POST, create GET, then the hotplug action
        mock_session.request.return_value.json.side_effect = [
            {"$key": drive_key, "name": "data-drive", "disksize": size},
            {"$key": drive_key, "name": "data-drive", "disksize": size, "machine": 200},
            {"task": 555},
        ]
        vm = VM(vm_data, mock_client.vms)

        result = vm.hotplug_drive(
            name="data-drive",
            size=size,
            interface="virtio-scsi",
            tier=2,
        )

        create_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(create_calls) == 1
        create_body = create_calls[0].kwargs.get("json", {})
        assert create_body["name"] == "data-drive"
        assert create_body["disksize"] == size
        assert create_body["interface"] == "virtio-scsi"
        assert create_body["media"] == "disk"
        assert create_body["preferred_tier"] == "2"

        action_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vm_actions" in call.kwargs.get("url", "")
        ]
        assert len(action_calls) == 1
        body = action_calls[0].kwargs.get("json", {})
        assert body["action"] == "hotplugdrive"
        assert body["vm"] == 100
        assert body["params"] == {"device": drive_key}
        assert result == {"task": 555}

    def test_hotplug_drive_rejects_partial_gib(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """A byte size that is not a whole GiB must not be truncated."""
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValueError, match="whole number of GiB"):
            vm.hotplug_drive(name="data-drive", size=512 * 1024**2)

        action_calls = [
            call
            for call in mock_session.request.call_args_list
            if "vm_actions" in call.kwargs.get("url", "")
        ]
        assert action_calls == []

    @pytest.mark.parametrize(
        ("interface", "media"),
        [
            ("ide", "disk"),
            ("ahci", "disk"),
            ("nvme", "disk"),
            ("virtio", "cdrom"),
            ("virtio-scsi", "cdrom"),
        ],
    )
    def test_hotplug_drive_rejects_unsupported_before_create(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
        interface: str,
        media: str,
    ) -> None:
        """ide/ahci/nvme and non-disk media must not create a drive."""
        vm = VM(vm_data, mock_client.vms)
        before = len(mock_session.request.call_args_list)

        with pytest.raises(ValueError, match="virtio"):
            vm.hotplug_drive(
                name="data-drive",
                size=1024**3,
                interface=interface,
                media=media,
            )

        new_calls = mock_session.request.call_args_list[before:]
        assert new_calls == []

    def test_hotplug_drive_deletes_drive_when_action_rejected(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """A rejected hotplug removes the drive it just created."""
        drive = {
            "$key": 77,
            "name": "data-drive",
            "disksize": 1024**3,
            "machine": 200,
            "media": "disk",
            "interface": "virtio",
        }
        mock_session.request.side_effect = [
            _http(200, drive),
            _http(200, drive),
            _http(422, {"err": "Machine must be in running state to hotplug"}),
            _http(200, drive),
            _http(204, None),
        ]
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValidationError, match="running state"):
            vm.hotplug_drive(name="data-drive", size=1024**3, interface="virtio")

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
            and "machine_drives/77" in call.kwargs.get("url", "")
        ]
        assert len(delete_calls) == 1

    def test_hotplug_drive_reraises_when_cleanup_delete_fails(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Cleanup failure must not hide the hotplug rejection."""
        drive = {
            "$key": 77,
            "name": "data-drive",
            "disksize": 1024**3,
            "machine": 200,
            "media": "disk",
            "interface": "virtio-scsi",
        }
        mock_session.request.side_effect = [
            _http(200, drive),
            _http(200, drive),
            _http(422, {"err": "Machine must be in running state to hotplug"}),
            _http(200, drive),
            _http(422, {"err": "cannot delete drive"}),
        ]
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValidationError, match="running state"):
            vm.hotplug_drive(name="data-drive", size=1024**3)

    def test_hotplug_nic(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Hotplug creates the NIC, then posts its key as device."""
        nic_key = 88
        # create POST, create GET, then the hotplug action
        mock_session.request.return_value.json.side_effect = [
            {"$key": nic_key, "name": "nic_1", "vnet": 10, "interface": "virtio"},
            {"$key": nic_key, "name": "nic_1", "vnet": 10, "interface": "virtio", "machine": 200},
            {"task": 666},
        ]
        vm = VM(vm_data, mock_client.vms)

        result = vm.hotplug_nic(name="nic_1", network=10, interface="virtio")

        create_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "machine_nics" in call.kwargs.get("url", "")
        ]
        assert len(create_calls) == 1
        create_body = create_calls[0].kwargs.get("json", {})
        assert create_body["name"] == "nic_1"
        assert create_body["vnet"] == 10
        assert create_body["interface"] == "virtio"

        action_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "vm_actions" in call.kwargs.get("url", "")
        ]
        assert len(action_calls) == 1
        body = action_calls[0].kwargs.get("json", {})
        assert body["action"] == "hotplugnic"
        assert body["vm"] == 100
        assert body["params"] == {"device": nic_key}
        assert result == {"task": 666}

    def test_hotplug_nic_deletes_nic_when_action_rejected(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """A rejected NIC hotplug removes the NIC it just created."""
        nic = {
            "$key": 88,
            "name": "nic_1",
            "vnet": 10,
            "interface": "virtio",
            "machine": 200,
        }
        mock_session.request.side_effect = [
            _http(200, nic),
            _http(200, nic),
            _http(422, {"err": "Machine must be in running state to hotplug"}),
            _http(200, nic),
            _http(204, None),
        ]
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValidationError, match="running state"):
            vm.hotplug_nic(name="nic_1", network=10, interface="virtio")

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
            and "machine_nics/88" in call.kwargs.get("url", "")
        ]
        assert len(delete_calls) == 1

    def test_tag(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test adding a tag to a VM via tag_members."""
        mock_session.request.return_value.json.return_value = {"$key": 999}
        vm = VM(vm_data, mock_client.vms)

        vm.tag(tag_key=15)

        # Check that POST was made to tag_members
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["tag"] == 15
        assert body["member"] == "vms/100"

    def test_untag(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test removing a tag from a VM via tag_members."""
        # First call: list members, second: delete
        responses = [
            MagicMock(
                status_code=200,
                text="[]",
                json=MagicMock(return_value=[{"$key": 555, "tag": 15, "member": "vms/100"}]),
            ),
            MagicMock(status_code=204, text=""),
        ]
        mock_session.request.side_effect = responses
        vm = VM(vm_data, mock_client.vms)

        vm.untag(tag_key=15)

        # Check that DELETE was made
        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1
        assert "tag_members/555" in delete_calls[0].kwargs["url"]

    def test_get_tags(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test getting tags assigned to a VM."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "tag": 10, "tag_name": "Production", "category_name": "Environment"},
            {"$key": 2, "tag": 20, "tag_name": "Web", "category_name": "Role"},
        ]
        vm = VM(vm_data, mock_client.vms)

        tags = vm.get_tags()

        assert len(tags) == 2
        assert tags[0]["tag_key"] == 10
        assert tags[0]["tag_name"] == "Production"
        assert tags[0]["category_name"] == "Environment"

    def test_favorite(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test adding VM to favorites."""
        # First call: lookup user by name, second: create favorite
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "name": "admin"}],  # GET users
            {"$key": 99},  # POST vm_favorites
        ]
        vm = VM(vm_data, mock_client.vms)

        vm.favorite()

        # Check that POST was made to vm_favorites
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["vm"] == 100
        assert body["user"] == 1

    def test_unfavorite(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test removing VM from favorites."""
        # Create separate mock objects for different calls
        responses = [
            MagicMock(
                status_code=200,
                text="[]",
                json=MagicMock(return_value=[{"$key": 1, "name": "admin"}]),
            ),
            MagicMock(
                status_code=200,
                text="[]",
                json=MagicMock(return_value=[{"$key": 99, "vm": 100, "user": 1}]),
            ),
            MagicMock(status_code=204, text=""),
        ]
        mock_session.request.side_effect = responses
        vm = VM(vm_data, mock_client.vms)

        vm.unfavorite()

        # Check that DELETE was made
        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1
        assert "vm_favorites/99" in delete_calls[0].kwargs["url"]

    def test_is_favorite_true(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test checking if VM is a favorite (true case)."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "name": "admin"}],  # GET users
            [{"$key": 99, "vm": 100, "user": 1}],  # GET vm_favorites
        ]
        vm = VM(vm_data, mock_client.vms)

        assert vm.is_favorite() is True

    def test_is_favorite_false(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test checking if VM is a favorite (false case)."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "name": "admin"}],  # GET users
            [],  # GET vm_favorites (empty)
        ]
        vm = VM(vm_data, mock_client.vms)

        assert vm.is_favorite() is False
