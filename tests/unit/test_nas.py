"""Unit tests for NAS service management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_services import (
    CIFSSettings,
    NASService,
    NASServiceManager,
    NFSSettings,
)
from pyvergeos.resources.nas_volumes import (
    NASVolume,
    NASVolumeManager,
    NASVolumeSnapshot,
    NASVolumeSnapshotManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def nas_manager(mock_client):
    """Create a NASServiceManager with mock client."""
    return NASServiceManager(mock_client)


@pytest.fixture
def sample_nas_service():
    """Sample NAS service data from API."""
    return {
        "$key": 1,
        "name": "NAS01",
        "vm": 10,
        "vm_name": "NAS01",
        "vm_status": "running",
        "vm_running": True,
        "vm_cores": 4,
        "vm_ram": 8589934592,
        "max_imports": 4,
        "max_syncs": 2,
        "disable_swap": False,
        "read_ahead_kb_default": 0,
        "cifs": 1,
        "nfs": 1,
        "volume_count": 3,
        "created": 1700000000,
        "modified": 1700001000,
    }


@pytest.fixture
def sample_cifs_settings():
    """Sample CIFS settings data from API."""
    return {
        "$key": 1,
        "service": 1,
        "service_name": "NAS01",
        "workgroup": "WORKGROUP",
        "realm": "",
        "server_type": "default",
        "map_to_guest": "bad user",
        "server_min_protocol": "SMB2",
        "extended_acl_support": True,
        "ad_status": "offline",
        "ad_status_info": "",
    }


@pytest.fixture
def sample_nfs_settings():
    """Sample NFS settings data from API."""
    return {
        "$key": 1,
        "service": 1,
        "service_name": "NAS01",
        "enable_nfsv4": True,
        "allowed_hosts": "192.168.1.0/24",
        "allow_all": False,
        "squash": "root_squash",
        "data_access": "rw",
        "anonuid": 65534,
        "anongid": 65534,
        "no_acl": False,
        "insecure": False,
        "async": False,
    }


class TestNASService:
    """Tests for NASService model."""

    def test_is_running_true(self, nas_manager, sample_nas_service):
        """Test is_running returns True when running."""
        service = NASService(sample_nas_service, nas_manager)
        assert service.is_running is True

    def test_is_running_false(self, nas_manager, sample_nas_service):
        """Test is_running returns False when stopped."""
        sample_nas_service["vm_running"] = False
        sample_nas_service["vm_status"] = "stopped"
        service = NASService(sample_nas_service, nas_manager)
        assert service.is_running is False

    def test_vm_key(self, nas_manager, sample_nas_service):
        """Test vm_key property."""
        service = NASService(sample_nas_service, nas_manager)
        assert service.vm_key == 10

    def test_vm_key_none(self, nas_manager, sample_nas_service):
        """Test vm_key returns None when not set."""
        sample_nas_service["vm"] = None
        service = NASService(sample_nas_service, nas_manager)
        assert service.vm_key is None

    def test_volume_count(self, nas_manager, sample_nas_service):
        """Test volume_count property."""
        service = NASService(sample_nas_service, nas_manager)
        assert service.volume_count == 3

    def test_volume_count_default(self, nas_manager):
        """Test volume_count defaults to 0."""
        service = NASService({"$key": 1}, nas_manager)
        assert service.volume_count == 0


class TestNASServiceManagerList:
    """Tests for NASServiceManager.list()."""

    def test_list_all(self, nas_manager, mock_client, sample_nas_service):
        """Test listing all NAS services."""
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.list()

        assert len(result) == 1
        assert result[0].name == "NAS01"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_services"

    def test_list_empty(self, nas_manager, mock_client):
        """Test listing when no NAS services exist."""
        mock_client._request.return_value = None

        result = nas_manager.list()

        assert result == []

    def test_list_with_filter(self, nas_manager, mock_client, sample_nas_service):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.list(filter="name eq 'NAS01'")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "name eq 'NAS01'"

    def test_list_with_status_filter(self, nas_manager, mock_client, sample_nas_service):
        """Test listing with status filter."""
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.list(status="running")

        assert len(result) == 1
        assert result[0].is_running is True

    def test_list_running(self, nas_manager, mock_client, sample_nas_service):
        """Test list_running helper."""
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.list_running()

        assert len(result) == 1
        assert result[0].is_running is True

    def test_list_stopped(self, nas_manager, mock_client, sample_nas_service):
        """Test list_stopped helper."""
        sample_nas_service["vm_running"] = False
        sample_nas_service["vm_status"] = "stopped"
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.list_stopped()

        assert len(result) == 1
        assert result[0].is_running is False


class TestNASServiceManagerGet:
    """Tests for NASServiceManager.get()."""

    def test_get_by_key(self, nas_manager, mock_client, sample_nas_service):
        """Test getting NAS service by key."""
        mock_client._request.return_value = sample_nas_service

        result = nas_manager.get(1)

        assert result.key == 1
        assert result.name == "NAS01"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_services/1"

    def test_get_by_name(self, nas_manager, mock_client, sample_nas_service):
        """Test getting NAS service by name."""
        mock_client._request.return_value = [sample_nas_service]

        result = nas_manager.get(name="NAS01")

        assert result.name == "NAS01"
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert "name eq 'NAS01'" in args[1]["params"]["filter"]

    def test_get_not_found(self, nas_manager, mock_client):
        """Test getting non-existent NAS service."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError):
            nas_manager.get(999)

    def test_get_by_name_not_found(self, nas_manager, mock_client):
        """Test getting non-existent NAS service by name."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError):
            nas_manager.get(name="nonexistent")

    def test_get_no_key_or_name(self, nas_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            nas_manager.get()


class TestNASServiceManagerCreate:
    """Tests for NASServiceManager.create()."""

    def test_create_basic(self, nas_manager, mock_client, sample_nas_service):
        """Test creating a basic NAS service."""
        # Mock recipe lookup
        mock_client._request.side_effect = [
            {"id": 1, "name": "Services"},  # Recipe lookup
            [],  # Check if exists (not found = good)
            {"$key": 1, "name": "Internal"},  # Network lookup
            None,  # Create recipe instance
            [sample_nas_service],  # Wait loop - get service
        ]

        result = nas_manager.create("NAS01")

        assert result.name == "NAS01"
        assert mock_client._request.call_count >= 4

    def test_create_with_options(self, nas_manager, mock_client, sample_nas_service):
        """Test creating NAS service with all options."""
        mock_client._request.side_effect = [
            {"id": 1, "name": "Services"},  # Recipe lookup
            [],  # Check if exists
            {"$key": 123, "name": "Internal"},  # Network lookup
            None,  # Create recipe instance
            [sample_nas_service],  # Wait loop - get service
        ]

        result = nas_manager.create(
            "NAS01",
            hostname="nas01",
            network="Internal",
            cores=8,
            memory_gb=16,
            auto_update=True,
        )

        assert result.name == "NAS01"

    def test_create_already_exists(self, nas_manager, mock_client, sample_nas_service):
        """Test creating NAS service that already exists."""
        mock_client._request.side_effect = [
            {"id": 1, "name": "Services"},  # Recipe lookup
            [sample_nas_service],  # Check if exists - found!
        ]

        with pytest.raises(ValueError, match="already exists"):
            nas_manager.create("NAS01")

    def test_create_no_recipe(self, nas_manager, mock_client):
        """Test creating NAS service without Services recipe."""
        mock_client._request.return_value = None

        with pytest.raises(ValueError, match="Services recipe not found"):
            nas_manager.create("NAS01")


class TestNASServiceManagerUpdate:
    """Tests for NASServiceManager.update()."""

    def test_update_service_settings(self, nas_manager, mock_client, sample_nas_service):
        """Test updating NAS service settings."""
        mock_client._request.side_effect = [
            sample_nas_service,  # Get current service
            None,  # Update service
            sample_nas_service,  # Get updated service
        ]

        result = nas_manager.update(1, max_imports=5, max_syncs=3)

        assert result is not None
        # Check the update call
        update_call = mock_client._request.call_args_list[1]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "vm_services/1"
        assert update_call[1]["json_data"]["max_imports"] == 5
        assert update_call[1]["json_data"]["max_syncs"] == 3

    def test_update_vm_settings(self, nas_manager, mock_client, sample_nas_service):
        """Test updating VM-level settings."""
        mock_client._request.side_effect = [
            sample_nas_service,  # Get current service
            None,  # Update VM
            sample_nas_service,  # Get updated service
        ]

        result = nas_manager.update(1, cpu_cores=8, memory_gb=16)

        assert result is not None
        # Check the VM update call
        update_call = mock_client._request.call_args_list[1]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "vms/10"
        assert update_call[1]["json_data"]["cpu_cores"] == 8
        assert update_call[1]["json_data"]["ram"] == 16 * 1024  # GB to MB


class TestNASServiceManagerDelete:
    """Tests for NASServiceManager.delete()."""

    def test_delete(self, nas_manager, mock_client, sample_nas_service):
        """Test deleting a stopped NAS service."""
        sample_nas_service["vm_running"] = False
        sample_nas_service["vm_status"] = "stopped"
        sample_nas_service["volume_count"] = 0
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            None,  # Delete VM
        ]

        nas_manager.delete(1)

        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vms/10"

    def test_delete_running_service(self, nas_manager, mock_client, sample_nas_service):
        """Test deleting a running NAS service fails."""
        mock_client._request.return_value = sample_nas_service

        with pytest.raises(ValueError, match="Service is running"):
            nas_manager.delete(1)

    def test_delete_with_volumes(self, nas_manager, mock_client, sample_nas_service):
        """Test deleting NAS service with volumes fails without force."""
        sample_nas_service["vm_running"] = False
        sample_nas_service["vm_status"] = "stopped"
        sample_nas_service["volume_count"] = 3
        mock_client._request.return_value = sample_nas_service

        with pytest.raises(ValueError, match="volume"):
            nas_manager.delete(1)

    def test_delete_force(self, nas_manager, mock_client, sample_nas_service):
        """Test force delete with volumes."""
        sample_nas_service["vm_running"] = False
        sample_nas_service["vm_status"] = "stopped"
        sample_nas_service["volume_count"] = 3
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            None,  # Delete VM
        ]

        nas_manager.delete(1, force=True)

        assert mock_client._request.call_count == 2


class TestNASServiceManagerPower:
    """Tests for NAS service power operations."""

    def test_power_on(self, nas_manager, mock_client, sample_nas_service):
        """Test powering on a NAS service."""
        sample_nas_service["vm_running"] = False
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            {"task": 123},  # Power on
        ]

        result = nas_manager.power_on(1)

        assert result == {"task": 123}
        power_call = mock_client._request.call_args_list[1]
        assert power_call[0][0] == "PUT"
        assert "action=poweron" in power_call[0][1]

    def test_power_off(self, nas_manager, mock_client, sample_nas_service):
        """Test powering off a NAS service."""
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            {"task": 123},  # Power off
        ]

        result = nas_manager.power_off(1)

        assert result == {"task": 123}
        power_call = mock_client._request.call_args_list[1]
        assert "action=poweroff" in power_call[0][1]

    def test_power_off_force(self, nas_manager, mock_client, sample_nas_service):
        """Test force power off."""
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            {"task": 123},  # Kill power
        ]

        result = nas_manager.power_off(1, force=True)

        assert result == {"task": 123}
        power_call = mock_client._request.call_args_list[1]
        assert "action=killpower" in power_call[0][1]

    def test_restart(self, nas_manager, mock_client, sample_nas_service):
        """Test restarting a NAS service."""
        mock_client._request.side_effect = [
            sample_nas_service,  # Get service
            {"task": 123},  # Reset
        ]

        result = nas_manager.restart(1)

        assert result == {"task": 123}
        reset_call = mock_client._request.call_args_list[1]
        assert "action=reset" in reset_call[0][1]


class TestNASServiceManagerCIFSSettings:
    """Tests for CIFS settings operations."""

    def test_get_cifs_settings(self, nas_manager, mock_client, sample_cifs_settings):
        """Test getting CIFS settings."""
        mock_client._request.return_value = [sample_cifs_settings]

        result = nas_manager.get_cifs_settings(1)

        assert isinstance(result, CIFSSettings)
        assert result.key == 1
        assert result.get("workgroup") == "WORKGROUP"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_service_cifs"

    def test_get_cifs_settings_not_found(self, nas_manager, mock_client):
        """Test getting CIFS settings when not found."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="CIFS settings not found"):
            nas_manager.get_cifs_settings(999)

    def test_set_cifs_settings(self, nas_manager, mock_client, sample_cifs_settings):
        """Test updating CIFS settings."""
        mock_client._request.side_effect = [
            [sample_cifs_settings],  # Get current settings
            None,  # Update
            [sample_cifs_settings],  # Get updated settings
        ]

        result = nas_manager.set_cifs_settings(1, workgroup="MYWORKGROUP")

        assert result is not None
        update_call = mock_client._request.call_args_list[1]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "vm_service_cifs/1"
        assert update_call[1]["json_data"]["workgroup"] == "myworkgroup"

    def test_set_cifs_min_protocol(self, nas_manager, mock_client, sample_cifs_settings):
        """Test setting minimum SMB protocol."""
        mock_client._request.side_effect = [
            [sample_cifs_settings],  # Get current settings
            None,  # Update
            [sample_cifs_settings],  # Get updated settings
        ]

        nas_manager.set_cifs_settings(1, min_protocol="SMB3")

        update_call = mock_client._request.call_args_list[1]
        assert update_call[1]["json_data"]["server_min_protocol"] == "SMB3"

    def test_set_cifs_guest_mapping(self, nas_manager, mock_client, sample_cifs_settings):
        """Test setting guest mapping."""
        mock_client._request.side_effect = [
            [sample_cifs_settings],  # Get current settings
            None,  # Update
            [sample_cifs_settings],  # Get updated settings
        ]

        nas_manager.set_cifs_settings(1, guest_mapping="never")

        update_call = mock_client._request.call_args_list[1]
        assert update_call[1]["json_data"]["map_to_guest"] == "never"


class TestNASServiceManagerNFSSettings:
    """Tests for NFS settings operations."""

    def test_get_nfs_settings(self, nas_manager, mock_client, sample_nfs_settings):
        """Test getting NFS settings."""
        mock_client._request.return_value = [sample_nfs_settings]

        result = nas_manager.get_nfs_settings(1)

        assert isinstance(result, NFSSettings)
        assert result.key == 1
        assert result.get("enable_nfsv4") is True
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_service_nfs"

    def test_get_nfs_settings_not_found(self, nas_manager, mock_client):
        """Test getting NFS settings when not found."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="NFS settings not found"):
            nas_manager.get_nfs_settings(999)

    def test_set_nfs_settings(self, nas_manager, mock_client, sample_nfs_settings):
        """Test updating NFS settings."""
        mock_client._request.side_effect = [
            [sample_nfs_settings],  # Get current settings
            None,  # Update
            [sample_nfs_settings],  # Get updated settings
        ]

        result = nas_manager.set_nfs_settings(1, enable_nfsv4=True)

        assert result is not None
        update_call = mock_client._request.call_args_list[1]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "vm_service_nfs/1"
        assert update_call[1]["json_data"]["enable_nfsv4"] is True

    def test_set_nfs_allowed_hosts(self, nas_manager, mock_client, sample_nfs_settings):
        """Test setting allowed hosts."""
        mock_client._request.side_effect = [
            [sample_nfs_settings],  # Get current settings
            None,  # Update
            [sample_nfs_settings],  # Get updated settings
        ]

        nas_manager.set_nfs_settings(1, allowed_hosts="192.168.1.0/24,10.0.0.0/8")

        update_call = mock_client._request.call_args_list[1]
        assert update_call[1]["json_data"]["allowed_hosts"] == "192.168.1.0/24,10.0.0.0/8"

    def test_set_nfs_squash(self, nas_manager, mock_client, sample_nfs_settings):
        """Test setting squash mode."""
        mock_client._request.side_effect = [
            [sample_nfs_settings],  # Get current settings
            None,  # Update
            [sample_nfs_settings],  # Get updated settings
        ]

        nas_manager.set_nfs_settings(1, squash="all_squash")

        update_call = mock_client._request.call_args_list[1]
        assert update_call[1]["json_data"]["squash"] == "all_squash"

    def test_set_nfs_data_access(self, nas_manager, mock_client, sample_nfs_settings):
        """Test setting data access mode."""
        mock_client._request.side_effect = [
            [sample_nfs_settings],  # Get current settings
            None,  # Update
            [sample_nfs_settings],  # Get updated settings
        ]

        nas_manager.set_nfs_settings(1, data_access="readonly")

        update_call = mock_client._request.call_args_list[1]
        assert update_call[1]["json_data"]["data_access"] == "ro"

    def test_set_nfs_no_changes(self, nas_manager, mock_client, sample_nfs_settings):
        """Test set_nfs_settings with no changes."""
        mock_client._request.return_value = [sample_nfs_settings]

        result = nas_manager.set_nfs_settings(1)

        # Should only call get, not update
        assert mock_client._request.call_count == 1
        assert result.key == 1


# =============================================================================
# NAS Volume Tests
# =============================================================================


@pytest.fixture
def nas_volume_manager(mock_client):
    """Create a NASVolumeManager with mock client."""
    return NASVolumeManager(mock_client)


@pytest.fixture
def sample_nas_volume():
    """Sample NAS volume data from API."""
    return {
        "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "id": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "name": "FileShare",
        "description": "Test file share",
        "enabled": True,
        "created": 1700000000,
        "modified": 1700001000,
        "maxsize": 107374182400,  # 100 GB
        "preferred_tier": "1",
        "fs_type": "ext4",
        "read_only": False,
        "discard": True,
        "owner_user": "root",
        "owner_group": "root",
        "encrypt": False,
        "automount_snapshots": False,
        "is_snapshot": False,
        "note": "",
        "creator": "admin",
        "service": 1,
        "service_display": "NAS01",
        "nas_vm_display": "NAS01",
        "nas_status": "running",
        "snapshot_profile": None,
        "snapshot_profile_display": None,
        "mount_status": "mounted",
        "mounted": True,
        "drive": 10,
        "used_bytes": 10737418240,  # 10 GB
        "allocated_bytes": 21474836480,  # 20 GB
    }


@pytest.fixture
def sample_nas_volume_snapshot():
    """Sample NAS volume snapshot data from API."""
    return {
        "$key": 1,
        "name": "pre-update",
        "description": "Snapshot before update",
        "created": 1700000000,
        "expires": 1700259200,  # 3 days later
        "expires_type": "date",
        "enabled": True,
        "created_manually": True,
        "quiesce": False,
        "volume": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "volume_display": "FileShare",
        "volume_name": "FileShare",
        "snap_volume": None,
    }


class TestNASVolume:
    """Tests for NASVolume model."""

    def test_key_is_string(self, nas_volume_manager, sample_nas_volume):
        """Test that volume key is a string (40-char hex)."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert isinstance(volume.key, str)
        assert len(volume.key) == 40

    def test_key_missing(self, nas_volume_manager):
        """Test key property raises ValueError when missing."""
        volume = NASVolume({}, nas_volume_manager)
        with pytest.raises(ValueError, match="has no \\$key"):
            _ = volume.key

    def test_max_size_gb(self, nas_volume_manager, sample_nas_volume):
        """Test max_size_gb property."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.max_size_gb == 100.0

    def test_max_size_gb_zero(self, nas_volume_manager):
        """Test max_size_gb returns 0 when not set."""
        volume = NASVolume({"$key": "abc123"}, nas_volume_manager)
        assert volume.max_size_gb == 0

    def test_used_gb(self, nas_volume_manager, sample_nas_volume):
        """Test used_gb property."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.used_gb == 10.0

    def test_allocated_gb(self, nas_volume_manager, sample_nas_volume):
        """Test allocated_gb property."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.allocated_gb == 20.0

    def test_is_mounted_true(self, nas_volume_manager, sample_nas_volume):
        """Test is_mounted returns True when mounted."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.is_mounted is True

    def test_is_mounted_false(self, nas_volume_manager, sample_nas_volume):
        """Test is_mounted returns False when not mounted."""
        sample_nas_volume["mounted"] = False
        sample_nas_volume["mount_status"] = "unmounted"
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.is_mounted is False

    def test_service_key(self, nas_volume_manager, sample_nas_volume):
        """Test service_key property."""
        volume = NASVolume(sample_nas_volume, nas_volume_manager)
        assert volume.service_key == 1

    def test_service_key_none(self, nas_volume_manager):
        """Test service_key returns None when not set."""
        volume = NASVolume({"$key": "abc123"}, nas_volume_manager)
        assert volume.service_key is None


class TestNASVolumeManagerList:
    """Tests for NASVolumeManager.list()."""

    def test_list_all(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test listing all volumes."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list()

        assert len(result) == 1
        assert result[0].name == "FileShare"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volumes"

    def test_list_empty(self, nas_volume_manager, mock_client):
        """Test listing when no volumes exist."""
        mock_client._request.return_value = None

        result = nas_volume_manager.list()

        assert result == []

    def test_list_with_filter(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list(filter="name eq 'FileShare'")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "name eq 'FileShare'"

    def test_list_with_enabled_filter(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test listing with enabled filter."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list(enabled=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "enabled eq 1" in args[1]["params"]["filter"]

    def test_list_with_fs_type_filter(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test listing with filesystem type filter."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list(fs_type="ext4")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "fs_type eq 'ext4'" in args[1]["params"]["filter"]

    def test_list_with_service_filter_by_key(
        self, nas_volume_manager, mock_client, sample_nas_volume
    ):
        """Test listing with service filter by key."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list(service=1)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "service eq 1" in args[1]["params"]["filter"]

    def test_list_with_service_filter_by_name(
        self, nas_volume_manager, mock_client, sample_nas_volume
    ):
        """Test listing with service filter by name."""
        mock_client._request.side_effect = [
            [{"$key": 1}],  # Service lookup
            [sample_nas_volume],  # Volume list
        ]

        result = nas_volume_manager.list(service="NAS01")

        assert len(result) == 1

    def test_list_with_pagination(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestNASVolumeManagerGet:
    """Tests for NASVolumeManager.get()."""

    def test_get_by_key(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test getting volume by key."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.get(key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result.name == "FileShare"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert "id eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_get_by_name(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test getting volume by name."""
        mock_client._request.return_value = [sample_nas_volume]

        result = nas_volume_manager.get(name="FileShare")

        assert result.name == "FileShare"
        args = mock_client._request.call_args
        assert "name eq 'FileShare'" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, nas_volume_manager, mock_client):
        """Test getting non-existent volume by key."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            nas_volume_manager.get(key="nonexistent")

    def test_get_not_found_by_name(self, nas_volume_manager, mock_client):
        """Test getting non-existent volume by name."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            nas_volume_manager.get(name="nonexistent")

    def test_get_no_key_or_name(self, nas_volume_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            nas_volume_manager.get()


class TestNASVolumeManagerCreate:
    """Tests for NASVolumeManager.create()."""

    def test_create_basic(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test creating a basic volume."""
        mock_client._request.side_effect = [
            None,  # Create volume
            [sample_nas_volume],  # Get created volume
        ]

        result = nas_volume_manager.create("FileShare", service=1, size_gb=100)

        assert result.name == "FileShare"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "volumes"
        assert create_call[1]["json_data"]["name"] == "FileShare"
        assert create_call[1]["json_data"]["service"] == 1
        assert create_call[1]["json_data"]["maxsize"] == 100 * 1073741824

    def test_create_with_all_options(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test creating volume with all options."""
        mock_client._request.side_effect = [
            None,  # Create volume
            [sample_nas_volume],  # Get created volume
        ]

        nas_volume_manager.create(
            "FileShare",
            service=1,
            size_gb=100,
            tier=2,
            description="Test volume",
            read_only=True,
            discard=False,
            owner_user="admin",
            owner_group="users",
            snapshot_profile=1,
            enabled=True,
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["name"] == "FileShare"
        assert body["preferred_tier"] == "2"
        assert body["description"] == "Test volume"
        assert body["read_only"] is True
        assert body["discard"] is False
        assert body["owner_user"] == "admin"
        assert body["owner_group"] == "users"
        assert body["snapshot_profile"] == 1

    def test_create_with_service_name(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test creating volume with service name."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            None,  # Create volume
            [sample_nas_volume],  # Get created volume
        ]

        result = nas_volume_manager.create("FileShare", service="NAS01", size_gb=100)

        assert result.name == "FileShare"
        create_call = mock_client._request.call_args_list[1]
        assert create_call[1]["json_data"]["service"] == 1

    def test_create_service_not_found(self, nas_volume_manager, mock_client):
        """Test creating volume with non-existent service."""
        mock_client._request.return_value = []

        with pytest.raises(ValueError, match="NAS service .* not found"):
            nas_volume_manager.create("FileShare", service="nonexistent", size_gb=100)


class TestNASVolumeManagerUpdate:
    """Tests for NASVolumeManager.update()."""

    def test_update_description(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test updating volume description."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        result = nas_volume_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            description="New description",
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in update_call[0][1]
        assert update_call[1]["json_data"]["description"] == "New description"

    def test_update_size(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test updating volume size."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        nas_volume_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            size_gb=200,
        )

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["maxsize"] == 200 * 1073741824

    def test_update_tier(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test updating volume tier."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        nas_volume_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            tier=3,
        )

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["preferred_tier"] == "3"

    def test_update_enabled(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test updating volume enabled state."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        nas_volume_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            enabled=False,
        )

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["enabled"] is False

    def test_update_no_changes(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test update with no changes."""
        mock_client._request.return_value = [sample_nas_volume]

        nas_volume_manager.update("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        # Should only call get, not update
        assert mock_client._request.call_count == 1


class TestNASVolumeManagerDelete:
    """Tests for NASVolumeManager.delete()."""

    def test_delete(self, nas_volume_manager, mock_client):
        """Test deleting a volume."""
        mock_client._request.return_value = None

        nas_volume_manager.delete("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in delete_call[0][1]


class TestNASVolumeManagerEnableDisable:
    """Tests for enable/disable operations."""

    def test_enable(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test enabling a volume."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        nas_volume_manager.enable("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["enabled"] is True

    def test_disable(self, nas_volume_manager, mock_client, sample_nas_volume):
        """Test disabling a volume."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_nas_volume],  # Get updated volume
        ]

        nas_volume_manager.disable("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["enabled"] is False


class TestNASVolumeManagerReset:
    """Tests for NASVolumeManager.reset()."""

    def test_reset(self, nas_volume_manager, mock_client):
        """Test resetting a volume."""
        mock_client._request.return_value = {"task": 123}

        result = nas_volume_manager.reset("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result == {"task": 123}
        reset_call = mock_client._request.call_args
        assert reset_call[0][0] == "PUT"
        assert "action=reset" in reset_call[0][1]


class TestNASVolumeManagerSnapshots:
    """Tests for NASVolumeManager.snapshots()."""

    def test_get_scoped_snapshot_manager(self, nas_volume_manager, mock_client):
        """Test getting a scoped snapshot manager."""
        vol_key = "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

        snap_mgr = nas_volume_manager.snapshots(vol_key)

        assert isinstance(snap_mgr, NASVolumeSnapshotManager)
        assert snap_mgr._volume_key == vol_key


# =============================================================================
# NAS Volume Snapshot Tests
# =============================================================================


@pytest.fixture
def nas_volume_snapshot_manager(mock_client):
    """Create a NASVolumeSnapshotManager with mock client."""
    return NASVolumeSnapshotManager(mock_client)


@pytest.fixture
def scoped_snapshot_manager(mock_client):
    """Create a scoped NASVolumeSnapshotManager with mock client."""
    return NASVolumeSnapshotManager(
        mock_client, volume_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


class TestNASVolumeSnapshot:
    """Tests for NASVolumeSnapshot model."""

    def test_volume_key(self, nas_volume_snapshot_manager, sample_nas_volume_snapshot):
        """Test volume_key property."""
        snapshot = NASVolumeSnapshot(sample_nas_volume_snapshot, nas_volume_snapshot_manager)
        # Volume keys are 40-char hex strings for NAS volumes
        assert snapshot.volume_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert isinstance(snapshot.volume_key, str)

    def test_never_expires_false(self, nas_volume_snapshot_manager, sample_nas_volume_snapshot):
        """Test never_expires returns False for dated expiration."""
        snapshot = NASVolumeSnapshot(sample_nas_volume_snapshot, nas_volume_snapshot_manager)
        assert snapshot.never_expires is False

    def test_never_expires_true_by_type(
        self, nas_volume_snapshot_manager, sample_nas_volume_snapshot
    ):
        """Test never_expires returns True when expires_type is never."""
        sample_nas_volume_snapshot["expires_type"] = "never"
        sample_nas_volume_snapshot["expires"] = 0
        snapshot = NASVolumeSnapshot(sample_nas_volume_snapshot, nas_volume_snapshot_manager)
        assert snapshot.never_expires is True

    def test_never_expires_true_by_value(
        self, nas_volume_snapshot_manager, sample_nas_volume_snapshot
    ):
        """Test never_expires returns True when expires is 0."""
        sample_nas_volume_snapshot["expires"] = 0
        snapshot = NASVolumeSnapshot(sample_nas_volume_snapshot, nas_volume_snapshot_manager)
        assert snapshot.never_expires is True


class TestNASVolumeSnapshotManagerList:
    """Tests for NASVolumeSnapshotManager.list()."""

    def test_list_all(self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot):
        """Test listing all snapshots."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        result = nas_volume_snapshot_manager.list()

        assert len(result) == 1
        assert result[0].name == "pre-update"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_snapshots"

    def test_list_empty(self, nas_volume_snapshot_manager, mock_client):
        """Test listing when no snapshots exist."""
        mock_client._request.return_value = None

        result = nas_volume_snapshot_manager.list()

        assert result == []

    def test_list_scoped_to_volume(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test listing snapshots scoped to a volume."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        result = scoped_snapshot_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "volume eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_list_with_volume_param_by_key(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test listing with volume parameter by key."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        result = nas_volume_snapshot_manager.list(volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "volume eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_list_with_volume_param_by_name(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test listing with volume parameter by name."""
        mock_client._request.side_effect = [
            [{"$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"}],  # Volume lookup
            [sample_nas_volume_snapshot],  # Snapshot list
        ]

        result = nas_volume_snapshot_manager.list(volume="FileShare")

        assert len(result) == 1

    def test_list_with_filter(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        nas_volume_snapshot_manager.list(filter="name eq 'pre-update'")

        args = mock_client._request.call_args
        assert "name eq 'pre-update'" in args[1]["params"]["filter"]

    def test_list_with_pagination(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        nas_volume_snapshot_manager.list(limit=10, offset=5)

        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestNASVolumeSnapshotManagerGet:
    """Tests for NASVolumeSnapshotManager.get()."""

    def test_get_by_key(self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot):
        """Test getting snapshot by key."""
        mock_client._request.return_value = sample_nas_volume_snapshot

        result = nas_volume_snapshot_manager.get(key=1)

        assert result.name == "pre-update"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_snapshots/1"

    def test_get_by_name(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test getting snapshot by name."""
        mock_client._request.return_value = [sample_nas_volume_snapshot]

        result = nas_volume_snapshot_manager.get(name="pre-update")

        assert result.name == "pre-update"
        args = mock_client._request.call_args
        assert "name eq 'pre-update'" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, nas_volume_snapshot_manager, mock_client):
        """Test getting non-existent snapshot by key."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            nas_volume_snapshot_manager.get(key=999)

    def test_get_not_found_by_name(self, nas_volume_snapshot_manager, mock_client):
        """Test getting non-existent snapshot by name."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            nas_volume_snapshot_manager.get(name="nonexistent")

    def test_get_no_key_or_name(self, nas_volume_snapshot_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            nas_volume_snapshot_manager.get()


class TestNASVolumeSnapshotManagerCreate:
    """Tests for NASVolumeSnapshotManager.create()."""

    def test_create_basic_scoped(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating a snapshot with scoped manager."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        result = scoped_snapshot_manager.create("pre-update")

        assert result.name == "pre-update"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "volume_snapshots"
        assert create_call[1]["json_data"]["name"] == "pre-update"
        assert create_call[1]["json_data"]["volume"] == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_create_with_volume_param(
        self, nas_volume_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating a snapshot with volume parameter."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        result = nas_volume_snapshot_manager.create(
            "pre-update",
            volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        )

        assert result.name == "pre-update"

    def test_create_no_volume(self, nas_volume_snapshot_manager):
        """Test creating snapshot without volume raises ValueError."""
        with pytest.raises(ValueError, match="Volume key is required"):
            nas_volume_snapshot_manager.create("pre-update")

    def test_create_with_description(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating snapshot with description."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        scoped_snapshot_manager.create(
            "pre-update",
            description="Snapshot before update",
        )

        create_call = mock_client._request.call_args_list[0]
        assert create_call[1]["json_data"]["description"] == "Snapshot before update"

    def test_create_with_custom_expiration(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating snapshot with custom expiration."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        scoped_snapshot_manager.create("pre-update", expires_days=7)

        create_call = mock_client._request.call_args_list[0]
        assert create_call[1]["json_data"]["expires_type"] == "date"
        assert create_call[1]["json_data"]["expires"] > 0

    def test_create_never_expires(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating snapshot that never expires."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        scoped_snapshot_manager.create("pre-update", never_expires=True)

        create_call = mock_client._request.call_args_list[0]
        assert create_call[1]["json_data"]["expires_type"] == "never"
        assert create_call[1]["json_data"]["expires"] == 0

    def test_create_with_quiesce(
        self, scoped_snapshot_manager, mock_client, sample_nas_volume_snapshot
    ):
        """Test creating snapshot with quiesce."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create snapshot
            sample_nas_volume_snapshot,  # Get created snapshot
        ]

        scoped_snapshot_manager.create("pre-update", quiesce=True)

        create_call = mock_client._request.call_args_list[0]
        assert create_call[1]["json_data"]["quiesce"] is True


class TestNASVolumeSnapshotManagerDelete:
    """Tests for NASVolumeSnapshotManager.delete()."""

    def test_delete(self, nas_volume_snapshot_manager, mock_client):
        """Test deleting a snapshot."""
        mock_client._request.return_value = None

        nas_volume_snapshot_manager.delete(1)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "volume_snapshots/1"
