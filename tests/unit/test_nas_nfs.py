"""Unit tests for NAS NFS share management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_nfs import NASNFSShare, NASNFSShareManager


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def nfs_manager(mock_client):
    """Create a NASNFSShareManager with mock client."""
    return NASNFSShareManager(mock_client)


@pytest.fixture
def sample_nfs_share():
    """Sample NFS share data from API."""
    return {
        "$key": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "id": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "name": "exports",
        "description": "NFS exports",
        "share_path": "/exports",
        "allowed_hosts": "192.168.1.0/24,10.0.0.0/8",
        "allow_all": False,
        "data_access": "rw",
        "squash": "root_squash",
        "fsid": "",
        "anonuid": 65534,
        "anongid": 65534,
        "no_acl": False,
        "insecure": False,
        "async": False,
        "enabled": True,
        "volume": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
        "volume_name": "FileShare",
        "volume_display": "FileShare",
        "status": "enabled",
        "state": "online",
        "created": 1700000000,
        "modified": 1700001000,
    }


class TestNASNFSShare:
    """Tests for NASNFSShare model."""

    def test_key_property(self, nfs_manager, sample_nfs_share):
        """Test key property returns 40-char hex string."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.key == "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        assert len(share.key) == 40

    def test_key_from_id(self, nfs_manager):
        """Test key property falls back to id field."""
        data = {"id": "feedfacefeedfacefeedfacefeedfacefeedface"}
        share = NASNFSShare(data, nfs_manager)
        assert share.key == "feedfacefeedfacefeedfacefeedfacefeedface"

    def test_key_missing_raises(self, nfs_manager):
        """Test key property raises ValueError when missing."""
        share = NASNFSShare({}, nfs_manager)
        with pytest.raises(ValueError, match="no \\$key"):
            _ = share.key

    def test_volume_key(self, nfs_manager, sample_nfs_share):
        """Test volume_key property."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.volume_key == "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"

    def test_volume_key_none(self, nfs_manager):
        """Test volume_key returns None when not set."""
        share = NASNFSShare({"$key": "abc123"}, nfs_manager)
        assert share.volume_key is None

    def test_volume_name(self, nfs_manager, sample_nfs_share):
        """Test volume_name property."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.volume_name == "FileShare"

    def test_volume_name_from_display(self, nfs_manager):
        """Test volume_name falls back to volume_display."""
        data = {"$key": "abc123", "volume_display": "BackupVol"}
        share = NASNFSShare(data, nfs_manager)
        assert share.volume_name == "BackupVol"

    def test_is_enabled_true(self, nfs_manager, sample_nfs_share):
        """Test is_enabled returns True when enabled."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.is_enabled is True

    def test_is_enabled_false(self, nfs_manager, sample_nfs_share):
        """Test is_enabled returns False when disabled."""
        sample_nfs_share["enabled"] = False
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.is_enabled is False

    def test_is_enabled_default(self, nfs_manager):
        """Test is_enabled defaults to False."""
        share = NASNFSShare({"$key": "abc123"}, nfs_manager)
        assert share.is_enabled is False

    def test_is_read_only_true(self, nfs_manager):
        """Test is_read_only returns True when data_access is ro."""
        data = {"$key": "abc123", "data_access": "ro"}
        share = NASNFSShare(data, nfs_manager)
        assert share.is_read_only is True

    def test_is_read_only_false(self, nfs_manager, sample_nfs_share):
        """Test is_read_only returns False when data_access is rw."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.is_read_only is False

    def test_allows_all_hosts_true(self, nfs_manager):
        """Test allows_all_hosts returns True when allow_all is set."""
        data = {"$key": "abc123", "allow_all": True}
        share = NASNFSShare(data, nfs_manager)
        assert share.allows_all_hosts is True

    def test_allows_all_hosts_false(self, nfs_manager, sample_nfs_share):
        """Test allows_all_hosts returns False by default."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.allows_all_hosts is False

    def test_squash_display_root_squash(self, nfs_manager, sample_nfs_share):
        """Test squash_display for root_squash."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.squash_display == "Squash Root"

    def test_squash_display_all_squash(self, nfs_manager):
        """Test squash_display for all_squash."""
        data = {"$key": "abc123", "squash": "all_squash"}
        share = NASNFSShare(data, nfs_manager)
        assert share.squash_display == "Squash All"

    def test_squash_display_no_root_squash(self, nfs_manager):
        """Test squash_display for no_root_squash."""
        data = {"$key": "abc123", "squash": "no_root_squash"}
        share = NASNFSShare(data, nfs_manager)
        assert share.squash_display == "No Squashing"

    def test_squash_display_unknown(self, nfs_manager):
        """Test squash_display for unknown value."""
        data = {"$key": "abc123", "squash": "custom_squash"}
        share = NASNFSShare(data, nfs_manager)
        assert share.squash_display == "custom_squash"

    def test_data_access_display_ro(self, nfs_manager):
        """Test data_access_display for ro."""
        data = {"$key": "abc123", "data_access": "ro"}
        share = NASNFSShare(data, nfs_manager)
        assert share.data_access_display == "Read Only"

    def test_data_access_display_rw(self, nfs_manager, sample_nfs_share):
        """Test data_access_display for rw."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        assert share.data_access_display == "Read and Write"

    def test_data_access_display_unknown(self, nfs_manager):
        """Test data_access_display for unknown value."""
        data = {"$key": "abc123", "data_access": "unknown"}
        share = NASNFSShare(data, nfs_manager)
        assert share.data_access_display == "unknown"


class TestNASNFSShareManagerList:
    """Tests for NASNFSShareManager.list()."""

    def test_list_all(self, nfs_manager, mock_client, sample_nfs_share):
        """Test listing all NFS shares."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.list()

        assert len(result) == 1
        assert result[0].name == "exports"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_nfs_shares"

    def test_list_empty(self, nfs_manager, mock_client):
        """Test listing returns empty list when no shares."""
        mock_client._request.return_value = []

        result = nfs_manager.list()

        assert result == []

    def test_list_with_volume_filter_by_key(self, nfs_manager, mock_client, sample_nfs_share):
        """Test listing shares filtered by volume key."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.list(volume="d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5")

        assert len(result) == 1
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params

    def test_list_with_enabled_filter(self, nfs_manager, mock_client, sample_nfs_share):
        """Test listing shares filtered by enabled status."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.list(enabled=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "enabled eq" in params["filter"]

    def test_list_with_limit(self, nfs_manager, mock_client, sample_nfs_share):
        """Test listing with limit parameter."""
        mock_client._request.return_value = [sample_nfs_share]

        nfs_manager.list(limit=10)

        args = mock_client._request.call_args
        params = args[1]["params"]
        assert params.get("limit") == 10


class TestNASNFSShareManagerGet:
    """Tests for NASNFSShareManager.get()."""

    def test_get_by_key(self, nfs_manager, mock_client, sample_nfs_share):
        """Test getting share by key."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.get("c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")

        assert result.name == "exports"
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "id eq 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4'" in params["filter"]

    def test_get_by_name(self, nfs_manager, mock_client, sample_nfs_share):
        """Test getting share by name."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.get(name="exports")

        assert result.key == "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "name eq 'exports'" in params["filter"]

    def test_get_by_name_with_volume(self, nfs_manager, mock_client, sample_nfs_share):
        """Test getting share by name and volume."""
        mock_client._request.return_value = [sample_nfs_share]

        result = nfs_manager.get(name="exports", volume="d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5")

        assert result.name == "exports"

    def test_get_not_found(self, nfs_manager, mock_client):
        """Test get raises NotFoundError when share not found."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="NFS share"):
            nfs_manager.get("nonexistent")

    def test_get_requires_key_or_name(self, nfs_manager):
        """Test get raises ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            nfs_manager.get()


class TestNASNFSShareManagerCreate:
    """Tests for NASNFSShareManager.create()."""

    def test_create_with_allowed_hosts(self, nfs_manager, mock_client, sample_nfs_share):
        """Test creating an NFS share with allowed hosts."""
        # Mock volume lookup
        mock_client._request.side_effect = [
            [{"$key": 123}],  # Volume lookup
            {"$key": sample_nfs_share["$key"]},  # Create response
            [sample_nfs_share],  # Get after create
        ]

        result = nfs_manager.create(
            name="exports", volume="FileShare", allowed_hosts=["192.168.1.0/24"]
        )

        assert result.name == "exports"

    def test_create_with_allow_all(self, nfs_manager, mock_client, sample_nfs_share):
        """Test creating an NFS share with allow_all."""
        sample_nfs_share["allow_all"] = True
        mock_client._request.side_effect = [
            [{"$key": 123}],  # Volume lookup
            {"$key": sample_nfs_share["$key"]},  # Create response
            [sample_nfs_share],  # Get after create
        ]

        result = nfs_manager.create(name="exports", volume="FileShare", allow_all=True)

        assert result.name == "exports"

    def test_create_requires_hosts_or_allow_all(self, nfs_manager, mock_client):
        """Test create requires either allowed_hosts or allow_all."""
        mock_client._request.return_value = [{"$key": 123}]  # Volume lookup

        with pytest.raises(ValueError, match="Either allowed_hosts or allow_all"):
            nfs_manager.create(name="exports", volume="FileShare")

    def test_create_with_all_options(self, nfs_manager, mock_client, sample_nfs_share):
        """Test creating a share with all options."""
        mock_client._request.side_effect = [
            [{"$key": 123}],  # Volume lookup
            {"$key": sample_nfs_share["$key"]},  # Create response
            [sample_nfs_share],  # Get after create
        ]

        result = nfs_manager.create(
            name="exports",
            volume="FileShare",
            share_path="/exports",
            description="Test NFS share",
            allowed_hosts=["192.168.1.0/24", "10.0.0.0/8"],
            data_access="rw",
            squash="root_squash",
            filesystem_id="",
            anonymous_uid=65534,
            anonymous_gid=65534,
            no_acl=False,
            insecure=False,
            async_mode=False,
            enabled=True,
        )

        assert result.name == "exports"
        # Verify POST was called
        calls = mock_client._request.call_args_list
        post_call = calls[1]
        assert post_call[0][0] == "POST"


class TestNASNFSShareManagerUpdate:
    """Tests for NASNFSShareManager.update()."""

    def test_update_description(self, nfs_manager, mock_client, sample_nfs_share):
        """Test updating share description."""
        updated_share = {**sample_nfs_share, "description": "Updated description"}
        mock_client._request.side_effect = [
            None,  # PUT response
            [updated_share],  # GET after update
        ]

        result = nfs_manager.update(sample_nfs_share["$key"], description="Updated description")

        assert result.get("description") == "Updated description"
        # Verify PUT was called
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"

    def test_update_access_settings(self, nfs_manager, mock_client, sample_nfs_share):
        """Test updating share access settings."""
        updated_share = {**sample_nfs_share, "data_access": "ro", "squash": "all_squash"}
        mock_client._request.side_effect = [
            None,  # PUT response
            [updated_share],  # GET after update
        ]

        result = nfs_manager.update(sample_nfs_share["$key"], data_access="ro", squash="all_squash")

        assert result.get("data_access") == "ro"
        assert result.get("squash") == "all_squash"

    def test_update_allowed_hosts(self, nfs_manager, mock_client, sample_nfs_share):
        """Test updating allowed hosts list."""
        updated_share = {**sample_nfs_share, "allowed_hosts": "10.0.0.0/8"}
        mock_client._request.side_effect = [
            None,  # PUT response
            [updated_share],  # GET after update
        ]

        result = nfs_manager.update(sample_nfs_share["$key"], allowed_hosts=["10.0.0.0/8"])

        assert result.get("allowed_hosts") == "10.0.0.0/8"


class TestNASNFSShareManagerDelete:
    """Tests for NASNFSShareManager.delete()."""

    def test_delete_share(self, nfs_manager, mock_client, sample_nfs_share):
        """Test deleting an NFS share."""
        mock_client._request.return_value = None

        nfs_manager.delete(sample_nfs_share["$key"])

        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "DELETE"
        assert sample_nfs_share["$key"] in args[0][1]


class TestNASNFSShareManagerEnableDisable:
    """Tests for enable/disable operations."""

    def test_enable_share(self, nfs_manager, mock_client, sample_nfs_share):
        """Test enabling an NFS share."""
        enabled_share = {**sample_nfs_share, "enabled": True}
        mock_client._request.side_effect = [
            None,  # PUT response
            [enabled_share],  # GET after update
        ]

        result = nfs_manager.enable(sample_nfs_share["$key"])

        assert result.is_enabled is True
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is True

    def test_disable_share(self, nfs_manager, mock_client, sample_nfs_share):
        """Test disabling an NFS share."""
        disabled_share = {**sample_nfs_share, "enabled": False}
        mock_client._request.side_effect = [
            None,  # PUT response
            [disabled_share],  # GET after update
        ]

        result = nfs_manager.disable(sample_nfs_share["$key"])

        assert result.is_enabled is False
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False


class TestNASNFSShareRefreshSaveDelete:
    """Tests for NASNFSShare instance methods."""

    def test_refresh(self, nfs_manager, mock_client, sample_nfs_share):
        """Test refreshing share from API."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        updated_share = {**sample_nfs_share, "description": "Refreshed"}
        mock_client._request.return_value = [updated_share]

        result = share.refresh()

        assert result.get("description") == "Refreshed"

    def test_save(self, nfs_manager, mock_client, sample_nfs_share):
        """Test saving share changes."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        updated_share = {**sample_nfs_share, "description": "New description"}
        mock_client._request.side_effect = [
            None,  # PUT
            [updated_share],  # GET
        ]

        result = share.save(description="New description")

        assert result.get("description") == "New description"

    def test_delete_instance(self, nfs_manager, mock_client, sample_nfs_share):
        """Test deleting share via instance method."""
        share = NASNFSShare(sample_nfs_share, nfs_manager)
        mock_client._request.return_value = None

        share.delete()

        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "DELETE"
