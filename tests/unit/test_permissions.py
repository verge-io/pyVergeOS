"""Unit tests for permission operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.permissions import Permission, PermissionManager


class TestPermission:
    """Tests for Permission resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        perm = Permission(data, MagicMock())
        assert perm.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        perm = Permission({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = perm.key

    def test_identity_key_property(self) -> None:
        """Test identity_key property."""
        data = {"$key": 1, "identity": 42}
        perm = Permission(data, MagicMock())
        assert perm.identity_key == 42

    def test_identity_key_default(self) -> None:
        """Test identity_key property defaults to 0."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.identity_key == 0

    def test_identity_name_property(self) -> None:
        """Test identity_name property."""
        data = {"$key": 1, "identity_display": "testuser"}
        perm = Permission(data, MagicMock())
        assert perm.identity_name == "testuser"

    def test_identity_name_none(self) -> None:
        """Test identity_name property when not set."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.identity_name is None

    def test_table_property(self) -> None:
        """Test table property."""
        data = {"$key": 1, "table": "vms"}
        perm = Permission(data, MagicMock())
        assert perm.table == "vms"

    def test_table_default(self) -> None:
        """Test table property defaults to empty string."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.table == ""

    def test_row_key_property(self) -> None:
        """Test row_key property."""
        data = {"$key": 1, "row": 5}
        perm = Permission(data, MagicMock())
        assert perm.row_key == 5

    def test_row_key_default(self) -> None:
        """Test row_key property defaults to 0."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.row_key == 0

    def test_row_display_property(self) -> None:
        """Test row_display property."""
        data = {"$key": 1, "rowdisplay": "Test VM"}
        perm = Permission(data, MagicMock())
        assert perm.row_display == "Test VM"

    def test_row_display_none(self) -> None:
        """Test row_display property when not set."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.row_display is None

    def test_is_table_level_true(self) -> None:
        """Test is_table_level property when row=0."""
        data = {"$key": 1, "row": 0}
        perm = Permission(data, MagicMock())
        assert perm.is_table_level is True

    def test_is_table_level_false(self) -> None:
        """Test is_table_level property when row>0."""
        data = {"$key": 1, "row": 5}
        perm = Permission(data, MagicMock())
        assert perm.is_table_level is False

    def test_can_list_property(self) -> None:
        """Test can_list property."""
        data = {"$key": 1, "list": True}
        perm = Permission(data, MagicMock())
        assert perm.can_list is True

    def test_can_list_default(self) -> None:
        """Test can_list property defaults to False."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.can_list is False

    def test_can_read_property(self) -> None:
        """Test can_read property."""
        data = {"$key": 1, "read": True}
        perm = Permission(data, MagicMock())
        assert perm.can_read is True

    def test_can_read_default(self) -> None:
        """Test can_read property defaults to False."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.can_read is False

    def test_can_create_property(self) -> None:
        """Test can_create property."""
        data = {"$key": 1, "create": True}
        perm = Permission(data, MagicMock())
        assert perm.can_create is True

    def test_can_create_default(self) -> None:
        """Test can_create property defaults to False."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.can_create is False

    def test_can_modify_property(self) -> None:
        """Test can_modify property."""
        data = {"$key": 1, "modify": True}
        perm = Permission(data, MagicMock())
        assert perm.can_modify is True

    def test_can_modify_default(self) -> None:
        """Test can_modify property defaults to False."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.can_modify is False

    def test_can_delete_property(self) -> None:
        """Test can_delete property."""
        data = {"$key": 1, "delete": True}
        perm = Permission(data, MagicMock())
        assert perm.can_delete is True

    def test_can_delete_default(self) -> None:
        """Test can_delete property defaults to False."""
        perm = Permission({"$key": 1}, MagicMock())
        assert perm.can_delete is False

    def test_has_full_control_true(self) -> None:
        """Test has_full_control property when all permissions granted."""
        data = {
            "$key": 1,
            "list": True,
            "read": True,
            "create": True,
            "modify": True,
            "delete": True,
        }
        perm = Permission(data, MagicMock())
        assert perm.has_full_control is True

    def test_has_full_control_false(self) -> None:
        """Test has_full_control property when not all permissions granted."""
        data = {
            "$key": 1,
            "list": True,
            "read": True,
            "create": False,  # Missing create
            "modify": True,
            "delete": True,
        }
        perm = Permission(data, MagicMock())
        assert perm.has_full_control is False

    def test_revoke_calls_manager(self) -> None:
        """Test revoke method calls manager."""
        manager = MagicMock(spec=PermissionManager)
        data = {"$key": 123}
        perm = Permission(data, manager)

        perm.revoke()

        manager.revoke.assert_called_once_with(123)


class TestPermissionManager:
    """Tests for PermissionManager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock VergeClient."""
        client = MagicMock()
        client._request = MagicMock()
        client.users = MagicMock()
        client.groups = MagicMock()
        return client

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> PermissionManager:
        """Create a PermissionManager with mock client."""
        return PermissionManager(mock_client)

    # List tests

    def test_list_returns_empty_when_none(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty list when API returns None."""
        mock_client._request.return_value = None

        result = manager.list()

        assert result == []

    def test_list_returns_permissions(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list returns Permission objects."""
        mock_client._request.return_value = [
            {"$key": 1, "identity": 10, "table": "vms", "row": 0},
            {"$key": 2, "identity": 10, "table": "vnets", "row": 0},
        ]

        result = manager.list()

        assert len(result) == 2
        assert isinstance(result[0], Permission)
        assert result[0].key == 1
        assert result[0].table == "vms"
        assert result[1].key == 2
        assert result[1].table == "vnets"

    def test_list_handles_single_object_response(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list handles single object response."""
        mock_client._request.return_value = {
            "$key": 1,
            "identity": 10,
            "table": "vms",
            "row": 0,
        }

        result = manager.list()

        assert len(result) == 1
        assert result[0].key == 1

    def test_list_with_user_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with user filter."""
        # Mock user lookup
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client.users.get.return_value = mock_user
        mock_client._request.return_value = []

        manager.list(user=1)

        # Verify request includes identity filter
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "identity eq 42" in call_args[1]["params"]["filter"]

    def test_list_with_user_object_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with User object filter."""
        # Create mock user object with identity
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client._request.return_value = []

        manager.list(user=mock_user)

        # Verify request includes identity filter (no user lookup needed)
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "identity eq 42" in call_args[1]["params"]["filter"]
        # Should not call users.get since we passed an object with identity
        mock_client.users.get.assert_not_called()

    def test_list_with_group_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with group filter."""
        # Mock group lookup
        mock_group = MagicMock()
        mock_group.identity = 55
        mock_client.groups.get.return_value = mock_group
        mock_client._request.return_value = []

        manager.list(group=2)

        # Verify request includes identity filter
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "identity eq 55" in call_args[1]["params"]["filter"]

    def test_list_with_table_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with table filter."""
        mock_client._request.return_value = []

        manager.list(table="vms")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "table eq 'vms'" in call_args[1]["params"]["filter"]

    def test_list_with_identity_key_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with identity_key filter."""
        mock_client._request.return_value = []

        manager.list(identity_key=99)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "identity eq 99" in call_args[1]["params"]["filter"]

    def test_list_with_limit(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test list with limit."""
        mock_client._request.return_value = []

        manager.list(limit=10)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10

    def test_list_with_offset(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test list with offset."""
        mock_client._request.return_value = []

        manager.list(offset=5)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["offset"] == 5

    def test_list_with_custom_fields(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list with custom fields."""
        mock_client._request.return_value = []

        manager.list(fields=["$key", "table"])

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["fields"] == "$key,table"

    def test_list_escapes_table_quotes(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test list escapes quotes in table filter."""
        mock_client._request.return_value = []

        manager.list(table="test'table")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "table eq 'test''table'" in call_args[1]["params"]["filter"]

    # Get tests

    def test_get_returns_permission(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test get returns Permission object."""
        mock_client._request.return_value = {
            "$key": 1,
            "identity": 10,
            "table": "vms",
            "row": 0,
        }

        result = manager.get(1)

        assert isinstance(result, Permission)
        assert result.key == 1
        assert result.table == "vms"

    def test_get_raises_not_found_when_none(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError when API returns None."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="Permission with key 1 not found"):
            manager.get(1)

    def test_get_raises_not_found_for_non_dict(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError for non-dict response."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="invalid response"):
            manager.get(1)

    def test_get_with_custom_fields(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test get with custom fields."""
        mock_client._request.return_value = {"$key": 1}

        manager.get(1, fields=["$key", "table"])

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["fields"] == "$key,table"

    # Grant tests

    def test_grant_with_user(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test grant permission to user."""
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client.users.get.return_value = mock_user
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "identity": 42, "table": "vms", "row": 0},  # GET response
        ]

        result = manager.grant(table="vms", user=1, can_list=True, can_read=True)

        assert isinstance(result, Permission)
        # Check POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        body = post_call[1]["json_data"]
        assert body["identity"] == 42
        assert body["table"] == "vms"
        assert body["row"] == 0
        assert body["list"] is True
        assert body["read"] is True
        assert body["create"] is False
        assert body["modify"] is False
        assert body["delete"] is False

    def test_grant_with_group(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test grant permission to group."""
        mock_group = MagicMock()
        mock_group.identity = 55
        mock_client.groups.get.return_value = mock_group
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "identity": 55, "table": "vnets", "row": 0},  # GET response
        ]

        result = manager.grant(table="vnets", group=2, can_list=True)

        assert isinstance(result, Permission)
        # Check POST was called with correct identity
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["identity"] == 55

    def test_grant_with_identity_key(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test grant permission with direct identity_key."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "identity": 99, "table": "vms", "row": 0},  # GET response
        ]

        result = manager.grant(table="vms", identity_key=99, can_list=True)

        assert isinstance(result, Permission)
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["identity"] == 99

    def test_grant_full_control(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test grant with full_control flag."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {
                "$key": 1,
                "identity": 99,
                "table": "vms",
                "row": 0,
                "list": True,
                "read": True,
                "create": True,
                "modify": True,
                "delete": True,
            },  # GET response
        ]

        result = manager.grant(table="vms", identity_key=99, full_control=True)

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["list"] is True
        assert body["read"] is True
        assert body["create"] is True
        assert body["modify"] is True
        assert body["delete"] is True
        assert result.has_full_control is True

    def test_grant_with_row_key(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test grant permission for specific row."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "identity": 99, "table": "vms", "row": 5},  # GET response
        ]

        result = manager.grant(table="vms", identity_key=99, row_key=5, can_list=True)

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["row"] == 5
        assert result.row_key == 5
        assert result.is_table_level is False

    def test_grant_raises_without_identity(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test grant raises ValueError without user/group/identity_key."""
        with pytest.raises(
            ValueError, match="Either user, group, or identity_key must be provided"
        ):
            manager.grant(table="vms", can_list=True)

    def test_grant_fallback_to_search(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test grant falls back to search when POST doesn't return $key."""
        mock_client._request.side_effect = [
            {},  # POST response without $key
            [{"$key": 1, "identity": 99, "table": "vms", "row": 0}],  # list response
        ]

        result = manager.grant(table="vms", identity_key=99, can_list=True)

        assert result.key == 1

    # Revoke tests

    def test_revoke_calls_delete(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test revoke calls DELETE endpoint."""
        mock_client._request.return_value = None

        manager.revoke(123)

        mock_client._request.assert_called_once_with("DELETE", "permissions/123")

    def test_revoke_for_user(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test revoke_for_user revokes all user permissions."""
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client.users.get.return_value = mock_user

        # First call returns list, subsequent calls are DELETEs
        mock_client._request.side_effect = [
            [
                {"$key": 1, "identity": 42, "table": "vms", "row": 0},
                {"$key": 2, "identity": 42, "table": "vnets", "row": 0},
            ],
            None,  # DELETE 1
            None,  # DELETE 2
        ]

        count = manager.revoke_for_user(1)

        assert count == 2
        # Verify DELETEs were called
        assert mock_client._request.call_count == 3
        mock_client._request.assert_any_call("DELETE", "permissions/1")
        mock_client._request.assert_any_call("DELETE", "permissions/2")

    def test_revoke_for_user_with_table_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test revoke_for_user with table filter."""
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client.users.get.return_value = mock_user

        mock_client._request.side_effect = [
            [{"$key": 1, "identity": 42, "table": "vms", "row": 0}],
            None,  # DELETE
        ]

        count = manager.revoke_for_user(1, table="vms")

        assert count == 1
        # Verify list was called with table filter
        list_call = mock_client._request.call_args_list[0]
        assert "table eq 'vms'" in list_call[1]["params"]["filter"]

    def test_revoke_for_group(self, manager: PermissionManager, mock_client: MagicMock) -> None:
        """Test revoke_for_group revokes all group permissions."""
        mock_group = MagicMock()
        mock_group.identity = 55
        mock_client.groups.get.return_value = mock_group

        mock_client._request.side_effect = [
            [
                {"$key": 1, "identity": 55, "table": "vms", "row": 0},
            ],
            None,  # DELETE
        ]

        count = manager.revoke_for_group(2)

        assert count == 1
        mock_client._request.assert_any_call("DELETE", "permissions/1")

    def test_revoke_for_group_with_table_filter(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test revoke_for_group with table filter."""
        mock_group = MagicMock()
        mock_group.identity = 55
        mock_client.groups.get.return_value = mock_group

        mock_client._request.side_effect = [
            [],  # No permissions found
        ]

        count = manager.revoke_for_group(2, table="vnets")

        assert count == 0
        # Verify list was called with table filter
        list_call = mock_client._request.call_args_list[0]
        assert "table eq 'vnets'" in list_call[1]["params"]["filter"]

    # Resolve identity tests

    def test_resolve_identity_with_user_object(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity with User object."""
        mock_user = MagicMock()
        mock_user.identity = 42

        result = manager._resolve_identity(user=mock_user)

        assert result == 42
        mock_client.users.get.assert_not_called()

    def test_resolve_identity_with_user_key(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity with user key."""
        mock_user = MagicMock()
        mock_user.identity = 42
        mock_client.users.get.return_value = mock_user

        result = manager._resolve_identity(user=1)

        assert result == 42
        mock_client.users.get.assert_called_once_with(1)

    def test_resolve_identity_with_group_object(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity with Group object."""
        mock_group = MagicMock()
        mock_group.identity = 55

        result = manager._resolve_identity(group=mock_group)

        assert result == 55
        mock_client.groups.get.assert_not_called()

    def test_resolve_identity_with_group_key(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity with group key."""
        mock_group = MagicMock()
        mock_group.identity = 55
        mock_client.groups.get.return_value = mock_group

        result = manager._resolve_identity(group=2)

        assert result == 55
        mock_client.groups.get.assert_called_once_with(2)

    def test_resolve_identity_with_identity_key(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity with direct identity_key."""
        result = manager._resolve_identity(identity_key=99)

        assert result == 99

    def test_resolve_identity_returns_none_without_args(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity returns None without arguments."""
        result = manager._resolve_identity()

        assert result is None

    def test_resolve_identity_prefers_identity_key(
        self, manager: PermissionManager, mock_client: MagicMock
    ) -> None:
        """Test _resolve_identity prefers identity_key over user/group."""
        mock_user = MagicMock()
        mock_user.identity = 42

        # identity_key should be used even if user is provided
        result = manager._resolve_identity(user=mock_user, identity_key=99)

        assert result == 99
