"""Integration tests for group and group member operations."""

import uuid
from contextlib import suppress

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def unique_name(prefix: str) -> str:
    """Generate a unique name for test resources."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestGroupOperations:
    """Integration tests for Group operations against live VergeOS."""

    def test_list_groups(self, live_client: VergeClient) -> None:
        """Test listing groups."""
        groups = live_client.groups.list()
        assert isinstance(groups, list)
        assert len(groups) >= 1  # At least default admin group exists

        # Each group should have expected fields
        group = groups[0]
        assert "$key" in group
        assert "name" in group
        assert "enabled" in group

    def test_list_with_member_count(self, live_client: VergeClient) -> None:
        """Test that list includes member_count."""
        groups = live_client.groups.list()
        assert len(groups) >= 1
        # member_count should be present (may be 0 or higher)
        assert "member_count" in groups[0]

    def test_list_enabled_groups(self, live_client: VergeClient) -> None:
        """Test listing enabled groups."""
        enabled = live_client.groups.list_enabled()
        assert isinstance(enabled, list)
        for group in enabled:
            assert group.is_enabled is True

    def test_list_exclude_system_groups(self, live_client: VergeClient) -> None:
        """Test listing groups excluding system groups."""
        non_system = live_client.groups.list(include_system=False)
        assert isinstance(non_system, list)
        for group in non_system:
            assert group.is_system_group is False

    def test_get_group_by_key(self, live_client: VergeClient) -> None:
        """Test getting a group by key."""
        groups = live_client.groups.list(limit=1)
        assert len(groups) >= 1

        group = live_client.groups.get(groups[0].key)
        assert group.key == groups[0].key
        assert group.name == groups[0].name

    def test_get_group_by_name(self, live_client: VergeClient) -> None:
        """Test getting a group by name."""
        groups = live_client.groups.list(limit=1)
        assert len(groups) >= 1

        group = live_client.groups.get(name=groups[0].name)
        assert group.name == groups[0].name
        assert group.key == groups[0].key

    def test_get_group_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent group."""
        with pytest.raises(NotFoundError):
            live_client.groups.get(name="nonexistent-group-xyz")


@pytest.mark.integration
class TestGroupCRUD:
    """Integration tests for Group CRUD operations against live VergeOS."""

    @pytest.fixture
    def test_group(self, live_client: VergeClient):
        """Create a test group for CRUD tests and cleanup afterwards."""
        name = unique_name("pytest_crud")
        group = live_client.groups.create(
            name=name,
            description="PyTest Test Group",
            email="pytest@test.local",
        )
        yield group
        # Cleanup
        with suppress(NotFoundError):
            live_client.groups.delete(group.key)

    def test_create_group(self, live_client: VergeClient) -> None:
        """Test creating a group."""
        name = unique_name("pytest_create")
        group = live_client.groups.create(
            name=name,
            description="Create Test Group",
            email="create@test.local",
        )

        try:
            assert group.name == name
            assert group.description == "Create Test Group"
            assert group.email == "create@test.local"
            assert group.is_enabled is True
        finally:
            live_client.groups.delete(group.key)

    def test_create_disabled_group(self, live_client: VergeClient) -> None:
        """Test creating a disabled group."""
        name = unique_name("pytest_disabled")
        group = live_client.groups.create(
            name=name,
            enabled=False,
        )

        try:
            assert group.is_enabled is False
        finally:
            live_client.groups.delete(group.key)

    def test_update_group_description(self, test_group, live_client: VergeClient) -> None:
        """Test updating group description."""
        updated = live_client.groups.update(
            test_group.key,
            description="Updated Description",
        )
        assert updated.description == "Updated Description"

    def test_update_group_email(self, test_group, live_client: VergeClient) -> None:
        """Test updating group email."""
        updated = live_client.groups.update(
            test_group.key,
            email="UPDATED@TEST.LOCAL",
        )
        assert updated.email == "updated@test.local"  # Should be lowercased

    def test_update_group_name(self, test_group, live_client: VergeClient) -> None:
        """Test updating group name."""
        new_name = unique_name("pytest_renamed")
        updated = live_client.groups.update(
            test_group.key,
            name=new_name,
        )
        assert updated.name == new_name

    def test_disable_group(self, test_group, live_client: VergeClient) -> None:
        """Test disabling a group."""
        updated = live_client.groups.disable(test_group.key)
        assert updated.is_enabled is False

    def test_enable_group(self, test_group, live_client: VergeClient) -> None:
        """Test enabling a group."""
        # First disable
        live_client.groups.disable(test_group.key)
        # Then enable
        updated = live_client.groups.enable(test_group.key)
        assert updated.is_enabled is True

    def test_delete_group(self, live_client: VergeClient) -> None:
        """Test deleting a group."""
        name = unique_name("pytest_delete")
        group = live_client.groups.create(name=name)
        group_key = group.key

        live_client.groups.delete(group_key)

        with pytest.raises(NotFoundError):
            live_client.groups.get(group_key)

    def test_group_object_enable(self, test_group, live_client: VergeClient) -> None:
        """Test enabling via group object method."""
        live_client.groups.disable(test_group.key)
        # Refresh to get disabled state
        group = live_client.groups.get(test_group.key)
        assert group.is_enabled is False

        enabled = group.enable()
        assert enabled.is_enabled is True

    def test_group_object_disable(self, test_group, live_client: VergeClient) -> None:
        """Test disabling via group object method."""
        group = live_client.groups.get(test_group.key)
        disabled = group.disable()
        assert disabled.is_enabled is False


@pytest.mark.integration
class TestGroupMemberOperations:
    """Integration tests for Group Member operations against live VergeOS."""

    @pytest.fixture
    def test_group(self, live_client: VergeClient):
        """Create a test group for member tests and cleanup afterwards."""
        name = unique_name("pytest_member")
        group = live_client.groups.create(
            name=name,
            description="Group for member tests",
        )
        yield group
        # Cleanup
        with suppress(NotFoundError):
            live_client.groups.delete(group.key)

    @pytest.fixture
    def test_child_group(self, live_client: VergeClient):
        """Create a child group for nested membership tests."""
        name = unique_name("pytest_child")
        group = live_client.groups.create(
            name=name,
            description="Child group for nesting",
        )
        yield group
        # Cleanup
        with suppress(NotFoundError):
            live_client.groups.delete(group.key)

    def test_list_members_empty(self, test_group, live_client: VergeClient) -> None:
        """Test listing members of a new group (should be empty)."""
        members = test_group.members.list()
        assert isinstance(members, list)
        assert len(members) == 0

    def test_add_user_to_group(self, test_group, live_client: VergeClient) -> None:
        """Test adding a user to a group."""
        # Get admin user to add
        admin = live_client.users.get(name="admin")

        member = test_group.members.add_user(admin.key)

        assert member.member_type == "User"
        assert member.member_key == admin.key
        assert member.member_name == "admin"

        # Cleanup
        test_group.members.remove_user(admin.key)

    def test_add_group_to_group(
        self, test_group, test_child_group, live_client: VergeClient
    ) -> None:
        """Test adding a group as member (nested group)."""
        member = test_group.members.add_group(test_child_group.key)

        assert member.member_type == "Group"
        assert member.member_key == test_child_group.key
        assert member.member_name == test_child_group.name

        # Cleanup
        test_group.members.remove_group(test_child_group.key)

    def test_list_members_with_user(self, test_group, live_client: VergeClient) -> None:
        """Test listing members includes added user."""
        admin = live_client.users.get(name="admin")
        test_group.members.add_user(admin.key)

        members = test_group.members.list()

        assert len(members) == 1
        assert members[0].member_type == "User"
        assert members[0].member_key == admin.key

        # Cleanup
        test_group.members.remove_user(admin.key)

    def test_remove_user_by_key(self, test_group, live_client: VergeClient) -> None:
        """Test removing user by membership key."""
        admin = live_client.users.get(name="admin")
        member = test_group.members.add_user(admin.key)

        test_group.members.remove(member.key)

        members = test_group.members.list()
        assert len(members) == 0

    def test_remove_user_by_user_key(self, test_group, live_client: VergeClient) -> None:
        """Test removing user using remove_user method."""
        admin = live_client.users.get(name="admin")
        test_group.members.add_user(admin.key)

        test_group.members.remove_user(admin.key)

        members = test_group.members.list()
        assert len(members) == 0

    def test_remove_group_from_group(
        self, test_group, test_child_group, live_client: VergeClient
    ) -> None:
        """Test removing nested group using remove_group method."""
        test_group.members.add_group(test_child_group.key)

        test_group.members.remove_group(test_child_group.key)

        members = test_group.members.list()
        assert len(members) == 0

    def test_remove_user_not_member(self, test_group, live_client: VergeClient) -> None:
        """Test removing a user that is not a member raises NotFoundError."""
        admin = live_client.users.get(name="admin")

        with pytest.raises(NotFoundError, match="not a member"):
            test_group.members.remove_user(admin.key)

    def test_member_object_remove(self, test_group, live_client: VergeClient) -> None:
        """Test removing member via member object method."""
        admin = live_client.users.get(name="admin")
        member = test_group.members.add_user(admin.key)

        member.remove()

        members = test_group.members.list()
        assert len(members) == 0

    def test_manager_members_method(self, test_group, live_client: VergeClient) -> None:
        """Test accessing members via client.groups.members()."""
        admin = live_client.users.get(name="admin")

        # Add via manager method
        live_client.groups.members(test_group.key).add_user(admin.key)

        # List via manager method
        members = live_client.groups.members(test_group.key).list()
        assert len(members) == 1

        # Remove via manager method
        live_client.groups.members(test_group.key).remove_user(admin.key)
        members = live_client.groups.members(test_group.key).list()
        assert len(members) == 0
