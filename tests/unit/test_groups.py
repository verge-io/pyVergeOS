"""Unit tests for group and group member operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.groups import (
    Group,
    GroupManager,
    GroupMember,
    GroupMemberManager,
)


class TestGroupMember:
    """Tests for GroupMember resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        member = GroupMember(data, MagicMock())
        assert member.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        member = GroupMember({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = member.key

    def test_group_key_property(self) -> None:
        """Test group_key property."""
        data = {"$key": 1, "parent_group": 5}
        member = GroupMember(data, MagicMock())
        assert member.group_key == 5

    def test_group_key_default(self) -> None:
        """Test group_key property defaults to 0."""
        member = GroupMember({"$key": 1}, MagicMock())
        assert member.group_key == 0

    def test_member_ref_property(self) -> None:
        """Test member_ref property."""
        data = {"$key": 1, "member": "/v4/users/10"}
        member = GroupMember(data, MagicMock())
        assert member.member_ref == "/v4/users/10"

    def test_member_ref_empty(self) -> None:
        """Test member_ref property when empty."""
        member = GroupMember({"$key": 1}, MagicMock())
        assert member.member_ref == ""

    def test_member_type_user(self) -> None:
        """Test member_type property for user."""
        data = {"$key": 1, "member": "/v4/users/10"}
        member = GroupMember(data, MagicMock())
        assert member.member_type == "User"

    def test_member_type_group(self) -> None:
        """Test member_type property for group."""
        data = {"$key": 1, "member": "/v4/groups/5"}
        member = GroupMember(data, MagicMock())
        assert member.member_type == "Group"

    def test_member_type_unknown(self) -> None:
        """Test member_type property for unknown ref."""
        data = {"$key": 1, "member": "/v4/other/1"}
        member = GroupMember(data, MagicMock())
        assert member.member_type == "Unknown"

    def test_member_key_user(self) -> None:
        """Test member_key property for user."""
        data = {"$key": 1, "member": "/v4/users/10"}
        member = GroupMember(data, MagicMock())
        assert member.member_key == 10

    def test_member_key_group(self) -> None:
        """Test member_key property for group."""
        data = {"$key": 1, "member": "/v4/groups/5"}
        member = GroupMember(data, MagicMock())
        assert member.member_key == 5

    def test_member_key_invalid(self) -> None:
        """Test member_key property for invalid ref."""
        data = {"$key": 1, "member": "/v4/users/invalid"}
        member = GroupMember(data, MagicMock())
        assert member.member_key is None

    def test_member_key_unknown(self) -> None:
        """Test member_key property for unknown type."""
        data = {"$key": 1, "member": "/v4/other/1"}
        member = GroupMember(data, MagicMock())
        assert member.member_key is None

    def test_member_name_property(self) -> None:
        """Test member_name property."""
        data = {"$key": 1, "member_display": "John Smith"}
        member = GroupMember(data, MagicMock())
        assert member.member_name == "John Smith"

    def test_member_name_none(self) -> None:
        """Test member_name property when not set."""
        member = GroupMember({"$key": 1}, MagicMock())
        assert member.member_name is None

    def test_creator_property(self) -> None:
        """Test creator property."""
        data = {"$key": 1, "creator": "admin"}
        member = GroupMember(data, MagicMock())
        assert member.creator == "admin"

    def test_creator_none(self) -> None:
        """Test creator property when not set."""
        member = GroupMember({"$key": 1}, MagicMock())
        assert member.creator is None

    def test_remove_method(self) -> None:
        """Test remove method calls manager."""
        mock_manager = MagicMock(spec=GroupMemberManager)
        data = {"$key": 123}
        member = GroupMember(data, mock_manager)

        member.remove()

        mock_manager.remove.assert_called_once_with(123)


class TestGroup:
    """Tests for Group resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        group = Group(data, MagicMock())
        assert group.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        group = Group({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = group.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "Administrators"}
        group = Group(data, MagicMock())
        assert group.name == "Administrators"

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Admin group"}
        group = Group(data, MagicMock())
        assert group.description == "Admin group"

    def test_description_none(self) -> None:
        """Test description property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.description is None

    def test_is_enabled_true(self) -> None:
        """Test is_enabled property when enabled."""
        data = {"$key": 1, "enabled": True}
        group = Group(data, MagicMock())
        assert group.is_enabled is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled property when disabled."""
        data = {"$key": 1, "enabled": False}
        group = Group(data, MagicMock())
        assert group.is_enabled is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled property defaults to True."""
        group = Group({"$key": 1}, MagicMock())
        assert group.is_enabled is True

    def test_email_property(self) -> None:
        """Test email property."""
        data = {"$key": 1, "email": "group@example.com"}
        group = Group(data, MagicMock())
        assert group.email == "group@example.com"

    def test_email_none(self) -> None:
        """Test email property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.email is None

    def test_identifier_property(self) -> None:
        """Test identifier property."""
        data = {"$key": 1, "id": "grp-001"}
        group = Group(data, MagicMock())
        assert group.identifier == "grp-001"

    def test_identifier_none(self) -> None:
        """Test identifier property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.identifier is None

    def test_identity_property(self) -> None:
        """Test identity property."""
        data = {"$key": 1, "identity": 5}
        group = Group(data, MagicMock())
        assert group.identity == 5

    def test_identity_none(self) -> None:
        """Test identity property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.identity is None

    def test_is_system_group_true(self) -> None:
        """Test is_system_group property when True."""
        data = {"$key": 1, "system_group": True}
        group = Group(data, MagicMock())
        assert group.is_system_group is True

    def test_is_system_group_false(self) -> None:
        """Test is_system_group property when False."""
        data = {"$key": 1, "system_group": False}
        group = Group(data, MagicMock())
        assert group.is_system_group is False

    def test_is_system_group_default(self) -> None:
        """Test is_system_group property defaults to False."""
        group = Group({"$key": 1}, MagicMock())
        assert group.is_system_group is False

    def test_member_count_property(self) -> None:
        """Test member_count property."""
        data = {"$key": 1, "member_count": 5}
        group = Group(data, MagicMock())
        assert group.member_count == 5

    def test_member_count_default(self) -> None:
        """Test member_count property defaults to 0."""
        group = Group({"$key": 1}, MagicMock())
        assert group.member_count == 0

    def test_created_property(self) -> None:
        """Test created property."""
        data = {"$key": 1, "created": 1700000000}
        group = Group(data, MagicMock())
        assert group.created == 1700000000

    def test_created_none(self) -> None:
        """Test created property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.created is None

    def test_creator_property(self) -> None:
        """Test creator property."""
        data = {"$key": 1, "creator": "admin"}
        group = Group(data, MagicMock())
        assert group.creator == "admin"

    def test_creator_none(self) -> None:
        """Test creator property when not set."""
        group = Group({"$key": 1}, MagicMock())
        assert group.creator is None

    def test_members_property(self) -> None:
        """Test members property returns GroupMemberManager."""
        mock_manager = MagicMock(spec=GroupManager)
        mock_member_manager = MagicMock(spec=GroupMemberManager)
        mock_manager.members.return_value = mock_member_manager

        data = {"$key": 123}
        group = Group(data, mock_manager)

        result = group.members

        mock_manager.members.assert_called_once_with(123)
        assert result == mock_member_manager

    def test_enable_method(self) -> None:
        """Test enable method calls manager."""
        mock_manager = MagicMock(spec=GroupManager)
        mock_manager.enable.return_value = Group({"$key": 1, "enabled": True}, mock_manager)

        data = {"$key": 1, "enabled": False}
        group = Group(data, mock_manager)

        result = group.enable()

        mock_manager.enable.assert_called_once_with(1)
        assert result.is_enabled is True

    def test_disable_method(self) -> None:
        """Test disable method calls manager."""
        mock_manager = MagicMock(spec=GroupManager)
        mock_manager.disable.return_value = Group({"$key": 1, "enabled": False}, mock_manager)

        data = {"$key": 1, "enabled": True}
        group = Group(data, mock_manager)

        result = group.disable()

        mock_manager.disable.assert_called_once_with(1)
        assert result.is_enabled is False


class TestGroupMemberManager:
    """Tests for GroupMemberManager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        return MagicMock()

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = GroupMemberManager(mock_client, group_key=5)
        assert manager._client == mock_client
        assert manager._group_key == 5
        assert manager._endpoint == "members"

    def test_list_empty(self, mock_client: MagicMock) -> None:
        """Test list returns empty list when no members."""
        mock_client._request.return_value = []
        manager = GroupMemberManager(mock_client, group_key=5)

        result = manager.list()

        assert result == []
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0] == ("GET", "members")
        assert "parent_group eq 5" in call_args[1]["params"]["filter"]

    def test_list_with_members(self, mock_client: MagicMock) -> None:
        """Test list returns GroupMember objects."""
        mock_client._request.return_value = [
            {"$key": 1, "parent_group": 5, "member": "/v4/users/10", "member_display": "John"},
            {"$key": 2, "parent_group": 5, "member": "/v4/groups/3", "member_display": "Admins"},
        ]
        manager = GroupMemberManager(mock_client, group_key=5)

        result = manager.list()

        assert len(result) == 2
        assert all(isinstance(m, GroupMember) for m in result)
        assert result[0].member_name == "John"
        assert result[0].member_type == "User"
        assert result[1].member_name == "Admins"
        assert result[1].member_type == "Group"

    def test_add_user(self, mock_client: MagicMock) -> None:
        """Test add_user creates membership."""
        # POST returns just the key
        mock_client._request.side_effect = [
            {"$key": 10},  # POST response
            [
                {
                    "$key": 10,
                    "parent_group": 5,
                    "member": "/v4/users/1",
                    "member_display": "testuser",
                }
            ],  # GET for list
        ]
        manager = GroupMemberManager(mock_client, group_key=5)

        result = manager.add_user(user_key=1)

        assert result.member_type == "User"
        assert result.member_key == 1
        # Check POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "members")
        assert post_call[1]["json_data"]["parent_group"] == 5
        assert post_call[1]["json_data"]["member"] == "/v4/users/1"

    def test_add_group(self, mock_client: MagicMock) -> None:
        """Test add_group creates nested group membership."""
        mock_client._request.side_effect = [
            {"$key": 11},  # POST response
            [
                {
                    "$key": 11,
                    "parent_group": 5,
                    "member": "/v4/groups/3",
                    "member_display": "ChildGroup",
                }
            ],  # GET for list
        ]
        manager = GroupMemberManager(mock_client, group_key=5)

        result = manager.add_group(member_group_key=3)

        assert result.member_type == "Group"
        assert result.member_key == 3
        # Check POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "members")
        assert post_call[1]["json_data"]["parent_group"] == 5
        assert post_call[1]["json_data"]["member"] == "/v4/groups/3"

    def test_remove(self, mock_client: MagicMock) -> None:
        """Test remove deletes membership."""
        mock_client._request.return_value = None
        manager = GroupMemberManager(mock_client, group_key=5)

        manager.remove(membership_key=10)

        mock_client._request.assert_called_once_with("DELETE", "members/10")

    def test_remove_user(self, mock_client: MagicMock) -> None:
        """Test remove_user finds and removes user membership."""
        mock_client._request.side_effect = [
            # First call is list() to find the membership
            [
                {
                    "$key": 10,
                    "parent_group": 5,
                    "member": "/v4/users/1",
                    "member_display": "testuser",
                }
            ],
            # Second call is delete
            None,
        ]
        manager = GroupMemberManager(mock_client, group_key=5)

        manager.remove_user(user_key=1)

        # Should have called list then delete
        assert mock_client._request.call_count == 2
        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0] == ("DELETE", "members/10")

    def test_remove_user_not_found(self, mock_client: MagicMock) -> None:
        """Test remove_user raises when user not a member."""
        mock_client._request.return_value = []
        manager = GroupMemberManager(mock_client, group_key=5)

        with pytest.raises(NotFoundError, match="not a member"):
            manager.remove_user(user_key=999)

    def test_remove_group(self, mock_client: MagicMock) -> None:
        """Test remove_group finds and removes group membership."""
        mock_client._request.side_effect = [
            # First call is list() to find the membership
            [
                {
                    "$key": 11,
                    "parent_group": 5,
                    "member": "/v4/groups/3",
                    "member_display": "ChildGroup",
                }
            ],
            # Second call is delete
            None,
        ]
        manager = GroupMemberManager(mock_client, group_key=5)

        manager.remove_group(member_group_key=3)

        # Should have called list then delete
        assert mock_client._request.call_count == 2
        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0] == ("DELETE", "members/11")

    def test_remove_group_not_found(self, mock_client: MagicMock) -> None:
        """Test remove_group raises when group not a member."""
        mock_client._request.return_value = []
        manager = GroupMemberManager(mock_client, group_key=5)

        with pytest.raises(NotFoundError, match="not a member"):
            manager.remove_group(member_group_key=999)


class TestGroupManager:
    """Tests for GroupManager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        return MagicMock()

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = GroupManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "groups"

    def test_list_empty(self, mock_client: MagicMock) -> None:
        """Test list returns empty list when no groups."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        result = manager.list()

        assert result == []

    def test_list_with_groups(self, mock_client: MagicMock) -> None:
        """Test list returns Group objects."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Administrators", "enabled": True},
            {"$key": 2, "name": "Developers", "enabled": True},
        ]
        manager = GroupManager(mock_client)

        result = manager.list()

        assert len(result) == 2
        assert all(isinstance(g, Group) for g in result)
        assert result[0].name == "Administrators"
        assert result[1].name == "Developers"

    def test_list_with_enabled_filter(self, mock_client: MagicMock) -> None:
        """Test list with enabled filter."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_with_disabled_filter(self, mock_client: MagicMock) -> None:
        """Test list with disabled filter."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        manager.list(enabled=False)

        call_args = mock_client._request.call_args
        assert "enabled eq false" in call_args[1]["params"]["filter"]

    def test_list_exclude_system_groups(self, mock_client: MagicMock) -> None:
        """Test list with include_system=False."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        manager.list(include_system=False)

        call_args = mock_client._request.call_args
        assert "system_group eq false" in call_args[1]["params"]["filter"]

    def test_list_enabled_convenience(self, mock_client: MagicMock) -> None:
        """Test list_enabled convenience method."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Admins", "enabled": True},
        ]
        manager = GroupManager(mock_client)

        result = manager.list_enabled()

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]
        assert len(result) == 1

    def test_list_disabled_convenience(self, mock_client: MagicMock) -> None:
        """Test list_disabled convenience method."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        result = manager.list_disabled()

        call_args = mock_client._request.call_args
        assert "enabled eq false" in call_args[1]["params"]["filter"]
        assert result == []

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test get by key."""
        mock_client._request.return_value = {"$key": 1, "name": "Admins"}
        manager = GroupManager(mock_client)

        result = manager.get(key=1)

        assert isinstance(result, Group)
        assert result.name == "Admins"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0] == ("GET", "groups/1")

    def test_get_by_key_not_found(self, mock_client: MagicMock) -> None:
        """Test get by key raises NotFoundError."""
        mock_client._request.return_value = None
        manager = GroupManager(mock_client)

        with pytest.raises(NotFoundError, match="not found"):
            manager.get(key=999)

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test get by name."""
        mock_client._request.return_value = [{"$key": 1, "name": "Admins"}]
        manager = GroupManager(mock_client)

        result = manager.get(name="Admins")

        assert isinstance(result, Group)
        assert result.name == "Admins"
        call_args = mock_client._request.call_args
        assert "name eq 'Admins'" in call_args[1]["params"]["filter"]

    def test_get_by_name_not_found(self, mock_client: MagicMock) -> None:
        """Test get by name raises NotFoundError."""
        mock_client._request.return_value = []
        manager = GroupManager(mock_client)

        with pytest.raises(NotFoundError, match="not found"):
            manager.get(name="Nonexistent")

    def test_get_no_args(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError when no args provided."""
        manager = GroupManager(mock_client)

        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_create_basic(self, mock_client: MagicMock) -> None:
        """Test basic group creation."""
        mock_client._request.side_effect = [
            {"$key": 5},  # POST response
            {"$key": 5, "name": "Developers", "enabled": True},  # GET response
        ]
        manager = GroupManager(mock_client)

        result = manager.create(name="Developers")

        assert isinstance(result, Group)
        assert result.name == "Developers"
        # Check POST was called correctly
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "groups")
        assert post_call[1]["json_data"]["name"] == "Developers"
        assert post_call[1]["json_data"]["enabled"] is True

    def test_create_with_all_options(self, mock_client: MagicMock) -> None:
        """Test group creation with all options."""
        mock_client._request.side_effect = [
            {"$key": 5},  # POST response
            {
                "$key": 5,
                "name": "QA Team",
                "description": "QA",
                "email": "qa@test.com",
                "enabled": True,
            },  # GET
        ]
        manager = GroupManager(mock_client)

        result = manager.create(
            name="QA Team",
            description="Quality Assurance",
            email="QA@TEST.COM",
            enabled=True,
        )

        assert isinstance(result, Group)
        # Check POST body
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["name"] == "QA Team"
        assert body["description"] == "Quality Assurance"
        assert body["email"] == "qa@test.com"  # Should be lowercased
        assert body["enabled"] is True

    def test_create_disabled(self, mock_client: MagicMock) -> None:
        """Test creating a disabled group."""
        mock_client._request.side_effect = [
            {"$key": 5},  # POST response
            {"$key": 5, "name": "Inactive", "enabled": False},  # GET response
        ]
        manager = GroupManager(mock_client)

        manager.create(name="Inactive", enabled=False)

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["enabled"] is False

    def test_update(self, mock_client: MagicMock) -> None:
        """Test group update."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "NewName", "description": "New desc"},  # GET response
        ]
        manager = GroupManager(mock_client)

        result = manager.update(key=1, name="NewName", description="New desc")

        assert isinstance(result, Group)
        # Check PUT was called
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "groups/1")
        assert put_call[1]["json_data"]["name"] == "NewName"
        assert put_call[1]["json_data"]["description"] == "New desc"

    def test_update_email_lowercased(self, mock_client: MagicMock) -> None:
        """Test update lowercases email."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "email": "test@example.com"},  # GET response
        ]
        manager = GroupManager(mock_client)

        manager.update(key=1, email="TEST@EXAMPLE.COM")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["email"] == "test@example.com"

    def test_update_empty_email(self, mock_client: MagicMock) -> None:
        """Test update with empty email clears it."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1},  # GET response
        ]
        manager = GroupManager(mock_client)

        manager.update(key=1, email="")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["email"] == ""

    def test_update_no_changes(self, mock_client: MagicMock) -> None:
        """Test update with no changes just returns current state."""
        mock_client._request.return_value = {"$key": 1, "name": "Admins"}
        manager = GroupManager(mock_client)

        manager.update(key=1)

        # Should only call GET, not PUT
        assert mock_client._request.call_count == 1
        assert mock_client._request.call_args[0][0] == "GET"

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test group deletion."""
        mock_client._request.return_value = None
        manager = GroupManager(mock_client)

        manager.delete(key=5)

        mock_client._request.assert_called_once_with("DELETE", "groups/5")

    def test_enable(self, mock_client: MagicMock) -> None:
        """Test enable method."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "enabled": True},  # GET response
        ]
        manager = GroupManager(mock_client)

        result = manager.enable(key=1)

        assert result.is_enabled is True
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is True

    def test_disable(self, mock_client: MagicMock) -> None:
        """Test disable method."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "enabled": False},  # GET response
        ]
        manager = GroupManager(mock_client)

        result = manager.disable(key=1)

        assert result.is_enabled is False
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False

    def test_members_method(self, mock_client: MagicMock) -> None:
        """Test members method returns GroupMemberManager."""
        manager = GroupManager(mock_client)

        result = manager.members(group_key=5)

        assert isinstance(result, GroupMemberManager)
        assert result._group_key == 5
        assert result._client == mock_client


class TestGroupManagerDefaultFields:
    """Tests for GroupManager default fields configuration."""

    def test_default_fields_include_key(self) -> None:
        """Test default fields include $key."""
        assert "$key" in GroupManager._default_fields

    def test_default_fields_include_name(self) -> None:
        """Test default fields include name."""
        assert "name" in GroupManager._default_fields

    def test_default_fields_include_description(self) -> None:
        """Test default fields include description."""
        assert "description" in GroupManager._default_fields

    def test_default_fields_include_enabled(self) -> None:
        """Test default fields include enabled."""
        assert "enabled" in GroupManager._default_fields

    def test_default_fields_include_member_count(self) -> None:
        """Test default fields include member count."""
        assert "count(members) as member_count" in GroupManager._default_fields

    def test_default_fields_include_system_group(self) -> None:
        """Test default fields include system_group."""
        assert "system_group" in GroupManager._default_fields
