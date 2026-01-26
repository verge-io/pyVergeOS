"""Integration tests for system user operations."""

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestUserOperations:
    """Integration tests for User operations against live VergeOS."""

    def test_list_users(self, live_client: VergeClient) -> None:
        """Test listing users."""
        users = live_client.users.list()
        assert isinstance(users, list)
        assert len(users) >= 1  # At least admin user exists

        # Each user should have expected fields
        user = users[0]
        assert "$key" in user
        assert "name" in user
        assert "type" in user
        assert "enabled" in user

    def test_list_excludes_system_users_by_default(self, live_client: VergeClient) -> None:
        """Test that list() excludes system users by default."""
        users = live_client.users.list()
        for user in users:
            assert user.user_type not in ("site_sync", "site_user")

    def test_list_enabled_users(self, live_client: VergeClient) -> None:
        """Test listing enabled users."""
        enabled = live_client.users.list_enabled()
        assert isinstance(enabled, list)
        for user in enabled:
            assert user.is_enabled is True

    def test_list_api_users(self, live_client: VergeClient) -> None:
        """Test listing API users."""
        api_users = live_client.users.list_api_users()
        assert isinstance(api_users, list)
        for user in api_users:
            assert user.user_type == "api"

    def test_get_user_by_key(self, live_client: VergeClient) -> None:
        """Test getting a user by key."""
        # First list to get a valid key
        users = live_client.users.list(limit=1)
        assert len(users) >= 1

        user = live_client.users.get(users[0].key)
        assert user.key == users[0].key
        assert user.name == users[0].name

    def test_get_user_by_name(self, live_client: VergeClient) -> None:
        """Test getting a user by name."""
        users = live_client.users.list(limit=1)
        assert len(users) >= 1

        user = live_client.users.get(name=users[0].name)
        assert user.name == users[0].name
        assert user.key == users[0].key

    def test_get_admin_user(self, live_client: VergeClient) -> None:
        """Test getting admin user by name."""
        admin = live_client.users.get(name="admin")
        assert admin.name == "admin"
        assert admin.is_enabled is True

    def test_get_user_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent user."""
        with pytest.raises(NotFoundError):
            live_client.users.get(name="nonexistent-user-xyz")


@pytest.mark.integration
class TestUserCRUD:
    """Integration tests for User CRUD operations against live VergeOS."""

    @pytest.fixture
    def test_user(self, live_client: VergeClient):
        """Create a test user for CRUD tests and cleanup afterwards."""
        user = live_client.users.create(
            name="pytest_testuser",
            password="TestPass123!",
            displayname="PyTest User",
            email="pytest@test.local",
        )
        yield user
        # Cleanup
        with contextlib.suppress(NotFoundError):
            live_client.users.delete(user.key)

    def test_create_user(self, live_client: VergeClient) -> None:
        """Test creating a user."""
        user = live_client.users.create(
            name="pytest_create_test",
            password="CreateTest123!",
            displayname="Create Test User",
            email="create@test.local",
        )

        try:
            assert user.name == "pytest_create_test"
            assert user.displayname == "Create Test User"
            assert user.email == "create@test.local"
            assert user.is_enabled is True
            assert user.user_type == "normal"
        finally:
            live_client.users.delete(user.key)

    def test_create_api_user(self, live_client: VergeClient) -> None:
        """Test creating an API user."""
        user = live_client.users.create(
            name="pytest_api_test",
            password="ApiTest123!",
            user_type="api",
        )

        try:
            assert user.name == "pytest_api_test"
            assert user.user_type == "api"
        finally:
            live_client.users.delete(user.key)

    def test_create_user_with_change_password(self, live_client: VergeClient) -> None:
        """Test creating a user with password change required."""
        user = live_client.users.create(
            name="pytest_pwd_test",
            password="TempPass123!",
            change_password=True,
        )

        try:
            assert user.change_password is True
        finally:
            live_client.users.delete(user.key)

    def test_update_user_displayname(self, test_user, live_client: VergeClient) -> None:
        """Test updating user displayname."""
        updated = live_client.users.update(
            test_user.key,
            displayname="Updated Display Name",
        )
        assert updated.displayname == "Updated Display Name"

    def test_update_user_email(self, test_user, live_client: VergeClient) -> None:
        """Test updating user email."""
        updated = live_client.users.update(
            test_user.key,
            email="updated@test.local",
        )
        assert updated.email == "updated@test.local"

    def test_update_user_password(self, test_user, live_client: VergeClient) -> None:
        """Test updating user password."""
        # This should not raise an error
        updated = live_client.users.update(
            test_user.key,
            password="NewPassword456!",
        )
        assert updated.key == test_user.key

    def test_disable_and_enable_user(self, test_user, live_client: VergeClient) -> None:
        """Test disabling and enabling a user."""
        # Disable
        disabled = live_client.users.disable(test_user.key)
        assert disabled.is_enabled is False

        # Enable
        enabled = live_client.users.enable(test_user.key)
        assert enabled.is_enabled is True

    def test_user_enable_method(self, live_client: VergeClient) -> None:
        """Test User.enable() method."""
        user = live_client.users.create(
            name="pytest_enable_method",
            password="EnableTest123!",
            enabled=False,
        )

        try:
            assert user.is_enabled is False

            # Use the method on the User object
            enabled = user.enable()
            assert enabled.is_enabled is True
        finally:
            live_client.users.delete(user.key)

    def test_user_disable_method(self, live_client: VergeClient) -> None:
        """Test User.disable() method."""
        user = live_client.users.create(
            name="pytest_disable_method",
            password="DisableTest123!",
            enabled=True,
        )

        try:
            assert user.is_enabled is True

            # Use the method on the User object
            disabled = user.disable()
            assert disabled.is_enabled is False
        finally:
            live_client.users.delete(user.key)

    def test_delete_user(self, live_client: VergeClient) -> None:
        """Test deleting a user."""
        user = live_client.users.create(
            name="pytest_delete_test",
            password="DeleteTest123!",
        )

        # Delete
        live_client.users.delete(user.key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.users.get(name="pytest_delete_test")


@pytest.mark.integration
class TestUserProperties:
    """Integration tests for User property access."""

    def test_admin_user_properties(self, live_client: VergeClient) -> None:
        """Test accessing properties on admin user."""
        admin = live_client.users.get(name="admin")

        # Basic properties
        assert admin.key is not None
        assert admin.name == "admin"
        assert admin.user_type in ("normal", "api", "vdi")
        assert admin.user_type_display in ("Normal", "API", "VDI")

        # Boolean properties
        assert isinstance(admin.is_enabled, bool)
        assert isinstance(admin.physical_access, bool)
        assert isinstance(admin.two_factor_enabled, bool)
        assert isinstance(admin.change_password, bool)
        assert isinstance(admin.is_locked, bool)

        # Numeric properties
        assert isinstance(admin.failed_attempts, int)

        # Timestamp properties
        assert admin.created is not None  # Admin should have creation time
        # last_login might be None if never logged in interactively

    def test_user_type_display(self, live_client: VergeClient) -> None:
        """Test user_type_display property."""
        user = live_client.users.create(
            name="pytest_type_display",
            password="TypeTest123!",
            user_type="api",
        )

        try:
            assert user.user_type == "api"
            assert user.user_type_display == "API"
        finally:
            live_client.users.delete(user.key)

    def test_two_factor_type_display(self, live_client: VergeClient) -> None:
        """Test two_factor_type_display property."""
        user = live_client.users.create(
            name="pytest_2fa_display",
            password="TwoFATest123!",
        )

        try:
            # Default is email
            assert user.two_factor_type in (None, "email")
            display = user.two_factor_type_display
            assert display in ("None", "Email")
        finally:
            live_client.users.delete(user.key)
