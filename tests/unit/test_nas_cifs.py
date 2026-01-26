"""Unit tests for NAS CIFS share management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_cifs import NASCIFSShare, NASCIFSShareManager


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def cifs_manager(mock_client):
    """Create a NASCIFSShareManager with mock client."""
    return NASCIFSShareManager(mock_client)


@pytest.fixture
def sample_cifs_share():
    """Sample CIFS share data from API."""
    return {
        "$key": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "id": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "name": "shared",
        "description": "Shared files",
        "share_path": "/shared",
        "comment": "Company shared drive",
        "enabled": True,
        "browseable": True,
        "read_only": False,
        "guest_ok": False,
        "guest_only": False,
        "force_user": "",
        "force_group": "",
        "valid_users": "user1\nuser2",
        "valid_groups": "admins\nusers",
        "admin_users": "admin",
        "admin_groups": "domain_admins",
        "host_allow": "192.168.1.0/24",
        "host_deny": "",
        "vfs_shadow_copy2": True,
        "volume": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
        "volume_name": "FileShare",
        "volume_display": "FileShare",
        "status": "enabled",
        "state": "online",
        "created": 1700000000,
        "modified": 1700001000,
    }


class TestNASCIFSShare:
    """Tests for NASCIFSShare model."""

    def test_key_property(self, cifs_manager, sample_cifs_share):
        """Test key property returns 40-char hex string."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.key == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        assert len(share.key) == 40

    def test_key_from_id(self, cifs_manager):
        """Test key property falls back to id field."""
        data = {"id": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}
        share = NASCIFSShare(data, cifs_manager)
        assert share.key == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    def test_key_missing_raises(self, cifs_manager):
        """Test key property raises ValueError when missing."""
        share = NASCIFSShare({}, cifs_manager)
        with pytest.raises(ValueError, match="no \\$key"):
            _ = share.key

    def test_volume_key(self, cifs_manager, sample_cifs_share):
        """Test volume_key property."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.volume_key == "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"

    def test_volume_key_none(self, cifs_manager):
        """Test volume_key returns None when not set."""
        share = NASCIFSShare({"$key": "abc123"}, cifs_manager)
        assert share.volume_key is None

    def test_volume_name(self, cifs_manager, sample_cifs_share):
        """Test volume_name property."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.volume_name == "FileShare"

    def test_volume_name_from_display(self, cifs_manager):
        """Test volume_name falls back to volume_display."""
        data = {"$key": "abc123", "volume_display": "BackupVol"}
        share = NASCIFSShare(data, cifs_manager)
        assert share.volume_name == "BackupVol"

    def test_is_enabled_true(self, cifs_manager, sample_cifs_share):
        """Test is_enabled returns True when enabled."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.is_enabled is True

    def test_is_enabled_false(self, cifs_manager, sample_cifs_share):
        """Test is_enabled returns False when disabled."""
        sample_cifs_share["enabled"] = False
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.is_enabled is False

    def test_is_enabled_default(self, cifs_manager):
        """Test is_enabled defaults to False."""
        share = NASCIFSShare({"$key": "abc123"}, cifs_manager)
        assert share.is_enabled is False

    def test_is_read_only_true(self, cifs_manager):
        """Test is_read_only returns True when read_only."""
        data = {"$key": "abc123", "read_only": True}
        share = NASCIFSShare(data, cifs_manager)
        assert share.is_read_only is True

    def test_is_read_only_false(self, cifs_manager, sample_cifs_share):
        """Test is_read_only returns False when read-write."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.is_read_only is False

    def test_allows_guests_true(self, cifs_manager):
        """Test allows_guests returns True when guest_ok."""
        data = {"$key": "abc123", "guest_ok": True}
        share = NASCIFSShare(data, cifs_manager)
        assert share.allows_guests is True

    def test_allows_guests_false(self, cifs_manager, sample_cifs_share):
        """Test allows_guests returns False by default."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.allows_guests is False

    def test_shadow_copy_enabled_true(self, cifs_manager, sample_cifs_share):
        """Test shadow_copy_enabled returns True when enabled."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        assert share.shadow_copy_enabled is True

    def test_shadow_copy_enabled_false(self, cifs_manager):
        """Test shadow_copy_enabled returns False when disabled."""
        data = {"$key": "abc123", "vfs_shadow_copy2": False}
        share = NASCIFSShare(data, cifs_manager)
        assert share.shadow_copy_enabled is False


class TestNASCIFSShareManagerList:
    """Tests for NASCIFSShareManager.list()."""

    def test_list_all(self, cifs_manager, mock_client, sample_cifs_share):
        """Test listing all CIFS shares."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.list()

        assert len(result) == 1
        assert result[0].name == "shared"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_cifs_shares"

    def test_list_empty(self, cifs_manager, mock_client):
        """Test listing returns empty list when no shares."""
        mock_client._request.return_value = []

        result = cifs_manager.list()

        assert result == []

    def test_list_with_volume_filter_by_key(self, cifs_manager, mock_client, sample_cifs_share):
        """Test listing shares filtered by volume key."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.list(volume="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3")

        assert len(result) == 1
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params

    def test_list_with_enabled_filter(self, cifs_manager, mock_client, sample_cifs_share):
        """Test listing shares filtered by enabled status."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.list(enabled=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "enabled eq" in params["filter"]

    def test_list_with_limit(self, cifs_manager, mock_client, sample_cifs_share):
        """Test listing with limit parameter."""
        mock_client._request.return_value = [sample_cifs_share]

        cifs_manager.list(limit=10)

        args = mock_client._request.call_args
        params = args[1]["params"]
        assert params.get("limit") == 10


class TestNASCIFSShareManagerGet:
    """Tests for NASCIFSShareManager.get()."""

    def test_get_by_key(self, cifs_manager, mock_client, sample_cifs_share):
        """Test getting share by key."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.get("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2")

        assert result.name == "shared"
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "id eq 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'" in params["filter"]

    def test_get_by_name(self, cifs_manager, mock_client, sample_cifs_share):
        """Test getting share by name."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.get(name="shared")

        assert result.key == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        args = mock_client._request.call_args
        params = args[1]["params"]
        assert "filter" in params
        assert "name eq 'shared'" in params["filter"]

    def test_get_by_name_with_volume(self, cifs_manager, mock_client, sample_cifs_share):
        """Test getting share by name and volume."""
        mock_client._request.return_value = [sample_cifs_share]

        result = cifs_manager.get(name="shared", volume="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3")

        assert result.name == "shared"

    def test_get_not_found(self, cifs_manager, mock_client):
        """Test get raises NotFoundError when share not found."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="CIFS share"):
            cifs_manager.get("nonexistent")

    def test_get_requires_key_or_name(self, cifs_manager):
        """Test get raises ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            cifs_manager.get()


class TestNASCIFSShareManagerCreate:
    """Tests for NASCIFSShareManager.create()."""

    def test_create_basic(self, cifs_manager, mock_client, sample_cifs_share):
        """Test creating a basic CIFS share."""
        # Mock volume lookup
        mock_client._request.side_effect = [
            [{"$key": 123}],  # Volume lookup
            {"$key": sample_cifs_share["$key"]},  # Create response
            [sample_cifs_share],  # Get after create
        ]

        result = cifs_manager.create(name="shared", volume="FileShare")

        assert result.name == "shared"

    def test_create_with_all_options(self, cifs_manager, mock_client, sample_cifs_share):
        """Test creating a share with all options."""
        mock_client._request.side_effect = [
            [{"$key": 123}],  # Volume lookup
            {"$key": sample_cifs_share["$key"]},  # Create response
            [sample_cifs_share],  # Get after create
        ]

        result = cifs_manager.create(
            name="shared",
            volume="FileShare",
            share_path="/shared",
            description="Test share",
            comment="Company files",
            browseable=True,
            read_only=False,
            guest_ok=False,
            guest_only=False,
            force_user="nobody",
            force_group="nogroup",
            valid_users=["user1", "user2"],
            valid_groups=["admins"],
            admin_users=["admin"],
            admin_groups=["domain_admins"],
            allowed_hosts=["192.168.1.0/24"],
            denied_hosts=[],
            shadow_copy=True,
            enabled=True,
        )

        assert result.name == "shared"
        # Verify POST was called
        calls = mock_client._request.call_args_list
        post_call = calls[1]
        assert post_call[0][0] == "POST"


class TestNASCIFSShareManagerUpdate:
    """Tests for NASCIFSShareManager.update()."""

    def test_update_description(self, cifs_manager, mock_client, sample_cifs_share):
        """Test updating share description."""
        updated_share = {**sample_cifs_share, "description": "Updated description"}
        mock_client._request.side_effect = [
            None,  # PUT response
            [updated_share],  # GET after update
        ]

        result = cifs_manager.update(sample_cifs_share["$key"], description="Updated description")

        assert result.get("description") == "Updated description"
        # Verify PUT was called
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"

    def test_update_access_settings(self, cifs_manager, mock_client, sample_cifs_share):
        """Test updating share access settings."""
        updated_share = {**sample_cifs_share, "guest_ok": True, "read_only": True}
        mock_client._request.side_effect = [
            None,  # PUT response
            [updated_share],  # GET after update
        ]

        result = cifs_manager.update(sample_cifs_share["$key"], guest_ok=True, read_only=True)

        assert result.get("guest_ok") is True
        assert result.get("read_only") is True


class TestNASCIFSShareManagerDelete:
    """Tests for NASCIFSShareManager.delete()."""

    def test_delete_share(self, cifs_manager, mock_client, sample_cifs_share):
        """Test deleting a CIFS share."""
        mock_client._request.return_value = None

        cifs_manager.delete(sample_cifs_share["$key"])

        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "DELETE"
        assert sample_cifs_share["$key"] in args[0][1]


class TestNASCIFSShareManagerEnableDisable:
    """Tests for enable/disable operations."""

    def test_enable_share(self, cifs_manager, mock_client, sample_cifs_share):
        """Test enabling a CIFS share."""
        enabled_share = {**sample_cifs_share, "enabled": True}
        mock_client._request.side_effect = [
            None,  # PUT response
            [enabled_share],  # GET after update
        ]

        result = cifs_manager.enable(sample_cifs_share["$key"])

        assert result.is_enabled is True
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is True

    def test_disable_share(self, cifs_manager, mock_client, sample_cifs_share):
        """Test disabling a CIFS share."""
        disabled_share = {**sample_cifs_share, "enabled": False}
        mock_client._request.side_effect = [
            None,  # PUT response
            [disabled_share],  # GET after update
        ]

        result = cifs_manager.disable(sample_cifs_share["$key"])

        assert result.is_enabled is False
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False


class TestNASCIFSShareRefreshSaveDelete:
    """Tests for NASCIFSShare instance methods."""

    def test_refresh(self, cifs_manager, mock_client, sample_cifs_share):
        """Test refreshing share from API."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        updated_share = {**sample_cifs_share, "description": "Refreshed"}
        mock_client._request.return_value = [updated_share]

        result = share.refresh()

        assert result.get("description") == "Refreshed"

    def test_save(self, cifs_manager, mock_client, sample_cifs_share):
        """Test saving share changes."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        updated_share = {**sample_cifs_share, "comment": "New comment"}
        mock_client._request.side_effect = [
            None,  # PUT
            [updated_share],  # GET
        ]

        result = share.save(comment="New comment")

        assert result.get("comment") == "New comment"

    def test_delete_instance(self, cifs_manager, mock_client, sample_cifs_share):
        """Test deleting share via instance method."""
        share = NASCIFSShare(sample_cifs_share, cifs_manager)
        mock_client._request.return_value = None

        share.delete()

        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "DELETE"
