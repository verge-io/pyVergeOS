"""Integration tests for permission operations."""

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestPermissionOperations:
    """Integration tests for Permission operations against live VergeOS."""

    @pytest.fixture
    def test_user(self, live_client: VergeClient):
        """Create a test user for permission tests and cleanup afterwards."""
        user = live_client.users.create(
            name="pytest_perm_user",
            password="TestPass123!",
            displayname="Permission Test User",
        )
        yield user
        # Cleanup - delete user (this should also clean up permissions)
        # Revoke permissions first
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_user(user.key)
        with contextlib.suppress(NotFoundError):
            live_client.users.delete(user.key)

    @pytest.fixture
    def test_group(self, live_client: VergeClient):
        """Create a test group for permission tests and cleanup afterwards."""
        group = live_client.groups.create(
            name="pytest_perm_group",
            description="Permission Test Group",
        )
        yield group
        # Cleanup - revoke permissions first
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_group(group.key)
        with contextlib.suppress(NotFoundError):
            live_client.groups.delete(group.key)

    def test_list_all_permissions(self, live_client: VergeClient) -> None:
        """Test listing all permissions."""
        perms = live_client.permissions.list(limit=10)
        assert isinstance(perms, list)
        # System should have at least some permissions
        assert len(perms) >= 1

        # Each permission should have expected fields
        perm = perms[0]
        assert "$key" in perm
        assert "identity" in perm
        assert "table" in perm

    def test_list_permissions_for_user(self, live_client: VergeClient, test_user) -> None:
        """Test listing permissions for a specific user."""
        # User should have default permissions after creation
        perms = live_client.permissions.list(user=test_user.key)
        assert isinstance(perms, list)
        # New users typically get some default permissions
        assert len(perms) >= 1

    def test_list_permissions_for_user_object(self, live_client: VergeClient, test_user) -> None:
        """Test listing permissions for a user object."""
        perms = live_client.permissions.list(user=test_user)
        assert isinstance(perms, list)
        # All returned permissions should be for this user
        for perm in perms:
            assert perm.identity_key == test_user.identity

    def test_list_permissions_by_table(self, live_client: VergeClient) -> None:
        """Test listing permissions filtered by table."""
        perms = live_client.permissions.list(table="/", limit=10)
        assert isinstance(perms, list)
        # All returned permissions should be for the root table
        for perm in perms:
            assert perm.table == "/"

    def test_list_permissions_with_pagination(self, live_client: VergeClient) -> None:
        """Test listing permissions with limit and offset."""
        # Get first page
        page1 = live_client.permissions.list(limit=2, offset=0)
        assert len(page1) <= 2

        # Get second page
        page2 = live_client.permissions.list(limit=2, offset=2)

        # Pages should be different (if there are enough permissions)
        if len(page1) == 2 and len(page2) >= 1:
            assert page1[0].key != page2[0].key

    def test_get_permission_by_key(self, live_client: VergeClient, test_user) -> None:
        """Test getting a permission by key."""
        # First list to get a valid key
        perms = live_client.permissions.list(user=test_user.key, limit=1)
        assert len(perms) >= 1

        perm = live_client.permissions.get(perms[0].key)
        assert perm.key == perms[0].key
        assert perm.identity_key == perms[0].identity_key
        assert perm.table == perms[0].table

    def test_get_permission_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent permission."""
        with pytest.raises(NotFoundError):
            live_client.permissions.get(999999)


@pytest.mark.integration
class TestPermissionGrant:
    """Integration tests for granting permissions."""

    @pytest.fixture
    def test_user(self, live_client: VergeClient):
        """Create a test user and cleanup afterwards."""
        user = live_client.users.create(
            name="pytest_grant_user",
            password="TestPass123!",
            displayname="Grant Test User",
        )
        yield user
        # Cleanup
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_user(user.key)
        with contextlib.suppress(NotFoundError):
            live_client.users.delete(user.key)

    @pytest.fixture
    def test_group(self, live_client: VergeClient):
        """Create a test group and cleanup afterwards."""
        import time

        group = live_client.groups.create(
            name=f"pytestgrntgrp{int(time.time()) % 10000}",
            description="Grant Test Group",
        )
        yield group
        # Cleanup
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_group(group.key)
        with contextlib.suppress(NotFoundError):
            live_client.groups.delete(group.key)

    def test_grant_read_only_to_user(self, live_client: VergeClient, test_user) -> None:
        """Test granting read-only permission to a user."""
        perm = live_client.permissions.grant(
            table="vms",
            user=test_user.key,
            can_list=True,
            can_read=True,
        )

        assert perm.table == "vms"
        assert perm.identity_key == test_user.identity
        assert perm.can_list is True
        assert perm.can_read is True
        assert perm.can_create is False
        assert perm.can_modify is False
        assert perm.can_delete is False
        assert perm.is_table_level is True

        # Cleanup
        live_client.permissions.revoke(perm.key)

    def test_grant_full_control_to_user(self, live_client: VergeClient, test_user) -> None:
        """Test granting full control to a user."""
        perm = live_client.permissions.grant(
            table="vnets",
            user=test_user.key,
            full_control=True,
        )

        assert perm.table == "vnets"
        assert perm.has_full_control is True
        assert perm.can_list is True
        assert perm.can_read is True
        assert perm.can_create is True
        assert perm.can_modify is True
        assert perm.can_delete is True

        # Cleanup
        live_client.permissions.revoke(perm.key)

    def test_grant_permission_to_group(self, live_client: VergeClient, test_group) -> None:
        """Test granting permission to a group."""
        perm = live_client.permissions.grant(
            table="volumes",
            group=test_group.key,
            can_list=True,
            can_read=True,
            can_create=True,
        )

        assert perm.table == "volumes"
        assert perm.identity_key == test_group.identity
        assert perm.can_list is True
        assert perm.can_read is True
        assert perm.can_create is True
        assert perm.can_modify is False
        assert perm.can_delete is False

        # Cleanup
        live_client.permissions.revoke(perm.key)

    def test_grant_permission_with_identity_key(self, live_client: VergeClient, test_user) -> None:
        """Test granting permission using identity_key directly."""
        perm = live_client.permissions.grant(
            table="tasks",
            identity_key=test_user.identity,
            can_list=True,
        )

        assert perm.table == "tasks"
        assert perm.identity_key == test_user.identity
        assert perm.can_list is True

        # Cleanup
        live_client.permissions.revoke(perm.key)


@pytest.mark.integration
class TestPermissionRevoke:
    """Integration tests for revoking permissions."""

    @pytest.fixture
    def test_user_with_perms(self, live_client: VergeClient):
        """Create a test user with permissions and cleanup afterwards."""
        user = live_client.users.create(
            name="pytest_revoke_user",
            password="TestPass123!",
        )
        # Grant some permissions
        live_client.permissions.grant(
            table="vms",
            user=user.key,
            can_list=True,
            can_read=True,
        )
        live_client.permissions.grant(
            table="vnets",
            user=user.key,
            can_list=True,
        )
        yield user
        # Cleanup
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_user(user.key)
        with contextlib.suppress(NotFoundError):
            live_client.users.delete(user.key)

    def test_revoke_permission_by_key(self, live_client: VergeClient, test_user_with_perms) -> None:
        """Test revoking a permission by key."""
        # Get user's permissions
        perms = live_client.permissions.list(user=test_user_with_perms.key)
        initial_count = len(perms)
        assert initial_count >= 2  # We granted 2 + default perms

        # Revoke one
        perm_to_revoke = None
        for p in perms:
            if p.table == "vms":
                perm_to_revoke = p
                break
        assert perm_to_revoke is not None

        live_client.permissions.revoke(perm_to_revoke.key)

        # Verify it's gone
        perms_after = live_client.permissions.list(user=test_user_with_perms.key)
        assert len(perms_after) == initial_count - 1

        # The specific permission should not be there
        for p in perms_after:
            assert p.key != perm_to_revoke.key

    def test_revoke_for_user(self, live_client: VergeClient) -> None:
        """Test revoking all permissions for a user."""
        # Create user
        user = live_client.users.create(
            name="pytest_revoke_all",
            password="TestPass123!",
        )
        try:
            # Grant some permissions
            live_client.permissions.grant(
                table="vms",
                user=user.key,
                can_list=True,
            )
            live_client.permissions.grant(
                table="vnets",
                user=user.key,
                can_list=True,
            )

            # Get count before
            perms_before = live_client.permissions.list(user=user.key)
            assert len(perms_before) >= 2

            # Revoke all
            count = live_client.permissions.revoke_for_user(user.key)
            assert count >= 2

            # Verify all are gone
            perms_after = live_client.permissions.list(user=user.key)
            assert len(perms_after) == 0
        finally:
            with contextlib.suppress(NotFoundError):
                live_client.users.delete(user.key)

    def test_revoke_for_user_with_table_filter(self, live_client: VergeClient) -> None:
        """Test revoking permissions for a user on a specific table."""
        # Create user
        user = live_client.users.create(
            name="pytest_revoke_tbl",
            password="TestPass123!",
        )
        try:
            # Grant permissions on different tables
            live_client.permissions.grant(
                table="vms",
                user=user.key,
                can_list=True,
            )
            live_client.permissions.grant(
                table="vnets",
                user=user.key,
                can_list=True,
            )

            # Revoke only vms permissions
            count = live_client.permissions.revoke_for_user(user.key, table="vms")
            assert count == 1

            # Verify vms permission is gone but vnets remains
            perms = live_client.permissions.list(user=user.key)
            tables = [p.table for p in perms]
            assert "vms" not in tables
            # Note: vnets permission may or may not be there depending on default perms

            # Cleanup remaining
            live_client.permissions.revoke_for_user(user.key)
        finally:
            with contextlib.suppress(NotFoundError):
                live_client.users.delete(user.key)

    def test_revoke_for_group(self, live_client: VergeClient) -> None:
        """Test revoking all permissions for a group."""
        import time

        # Create group
        group = live_client.groups.create(
            name=f"pytestrevgrp{int(time.time()) % 10000}",
            description="Test Group",
        )
        try:
            # Grant permissions
            live_client.permissions.grant(
                table="vms",
                group=group.key,
                can_list=True,
            )
            live_client.permissions.grant(
                table="vnets",
                group=group.key,
                can_list=True,
            )

            # Revoke all
            count = live_client.permissions.revoke_for_group(group.key)
            assert count == 2

            # Verify all are gone
            perms_after = live_client.permissions.list(group=group.key)
            assert len(perms_after) == 0
        finally:
            with contextlib.suppress(NotFoundError):
                live_client.groups.delete(group.key)


@pytest.mark.integration
class TestPermissionObject:
    """Integration tests for Permission object methods."""

    @pytest.fixture
    def test_user(self, live_client: VergeClient):
        """Create a test user and cleanup afterwards."""
        user = live_client.users.create(
            name="pytest_permobj",
            password="TestPass123!",
        )
        yield user
        # Cleanup
        with contextlib.suppress(Exception):
            live_client.permissions.revoke_for_user(user.key)
        with contextlib.suppress(NotFoundError):
            live_client.users.delete(user.key)

    def test_permission_revoke_method(self, live_client: VergeClient, test_user) -> None:
        """Test the Permission.revoke() method."""
        # Grant a permission
        perm = live_client.permissions.grant(
            table="files",
            user=test_user.key,
            can_list=True,
        )
        perm_key = perm.key

        # Use the object method to revoke
        perm.revoke()

        # Verify it's gone
        with pytest.raises(NotFoundError):
            live_client.permissions.get(perm_key)

    def test_permission_properties(self, live_client: VergeClient, test_user) -> None:
        """Test Permission object properties."""
        perm = live_client.permissions.grant(
            table="clusters",
            user=test_user.key,
            can_list=True,
            can_read=True,
            can_create=True,
            can_modify=True,
            can_delete=True,
        )
        try:
            # Test identity properties
            assert perm.identity_key == test_user.identity
            assert perm.identity_name is not None

            # Test table properties
            assert perm.table == "clusters"
            assert perm.row_key == 0
            assert perm.is_table_level is True

            # Test permission properties
            assert perm.can_list is True
            assert perm.can_read is True
            assert perm.can_create is True
            assert perm.can_modify is True
            assert perm.can_delete is True
            assert perm.has_full_control is True
        finally:
            live_client.permissions.revoke(perm.key)
