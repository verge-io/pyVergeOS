"""Integration tests for API key operations."""

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.api_keys import APIKey, APIKeyCreated


@pytest.mark.integration
class TestAPIKeyOperations:
    """Integration tests for API key operations against live VergeOS."""

    def test_list_api_keys(self, live_client: VergeClient) -> None:
        """Test listing API keys."""
        api_keys = live_client.api_keys.list()
        assert isinstance(api_keys, list)

        # Each key should have expected fields
        if len(api_keys) > 0:
            api_key = api_keys[0]
            assert "$key" in api_key
            assert "name" in api_key
            assert "user" in api_key

    def test_list_api_keys_for_user(self, live_client: VergeClient) -> None:
        """Test listing API keys for a specific user."""
        # Get admin user
        admin = live_client.users.get(name="admin")

        # List keys for admin
        keys = live_client.api_keys.list(user="admin")
        assert isinstance(keys, list)

        # All keys should belong to admin
        for key in keys:
            assert key.user_key == admin.key

    def test_list_api_keys_for_user_by_key(self, live_client: VergeClient) -> None:
        """Test listing API keys for a user by key."""
        admin = live_client.users.get(name="admin")

        keys = live_client.api_keys.list(user=admin.key)
        assert isinstance(keys, list)

        for key in keys:
            assert key.user_key == admin.key

    def test_get_api_key_by_key(self, live_client: VergeClient) -> None:
        """Test getting an API key by key."""
        # First list to get a valid key
        keys = live_client.api_keys.list(limit=1)
        if len(keys) == 0:
            pytest.skip("No API keys exist")

        api_key = live_client.api_keys.get(keys[0].key)
        assert api_key.key == keys[0].key
        assert api_key.name == keys[0].name

    def test_get_api_key_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent API key."""
        with pytest.raises(NotFoundError):
            live_client.api_keys.get(999999)


@pytest.mark.integration
class TestAPIKeyCRUD:
    """Integration tests for API key CRUD operations."""

    @pytest.fixture
    def test_api_key(self, live_client: VergeClient):
        """Create a test API key for CRUD tests and cleanup afterwards."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_test_key",
            description="PyTest integration test key",
        )
        yield result
        # Cleanup
        with contextlib.suppress(NotFoundError):
            live_client.api_keys.delete(result.key)

    def test_create_api_key(self, live_client: VergeClient) -> None:
        """Test creating an API key."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_create_test",
            description="Created by pytest",
        )

        try:
            assert isinstance(result, APIKeyCreated)
            assert result.name == "pytest_create_test"
            assert result.user_name == "admin"
            assert result.secret is not None
            assert len(result.secret) > 0

            # Verify key exists
            api_key = live_client.api_keys.get(result.key)
            assert api_key.name == "pytest_create_test"
            assert api_key.description == "Created by pytest"
        finally:
            live_client.api_keys.delete(result.key)

    def test_create_api_key_with_expiration(self, live_client: VergeClient) -> None:
        """Test creating an API key with expiration."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_expire_test",
            expires_in="30d",
        )

        try:
            api_key = live_client.api_keys.get(result.key)
            assert api_key.expires is not None
            assert api_key.expires_datetime is not None
            assert api_key.is_expired is False
        finally:
            live_client.api_keys.delete(result.key)

    def test_create_api_key_with_ip_restrictions(self, live_client: VergeClient) -> None:
        """Test creating an API key with IP restrictions."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_ip_test",
            ip_allow_list=["10.0.0.0/8", "192.168.1.100"],
            ip_deny_list=["10.0.0.1"],
        )

        try:
            api_key = live_client.api_keys.get(result.key)
            assert "10.0.0.0/8" in api_key.ip_allow_list
            assert "192.168.1.100" in api_key.ip_allow_list
            assert "10.0.0.1" in api_key.ip_deny_list
        finally:
            live_client.api_keys.delete(result.key)

    def test_create_api_key_never_expires(self, live_client: VergeClient) -> None:
        """Test creating an API key that never expires."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_never_expire_test",
            expires_in="never",
        )

        try:
            api_key = live_client.api_keys.get(result.key)
            assert api_key.expires is None
            assert api_key.is_expired is False
        finally:
            live_client.api_keys.delete(result.key)

    def test_create_api_key_with_user_key(self, live_client: VergeClient) -> None:
        """Test creating an API key with user key instead of name."""
        admin = live_client.users.get(name="admin")

        result = live_client.api_keys.create(
            user=admin.key,
            name="pytest_user_key_test",
        )

        try:
            api_key = live_client.api_keys.get(result.key)
            assert api_key.user_key == admin.key
        finally:
            live_client.api_keys.delete(result.key)

    def test_get_api_key_by_name(self, test_api_key, live_client: VergeClient) -> None:
        """Test getting an API key by name."""
        api_key = live_client.api_keys.get(
            name="pytest_test_key",
            user="admin",
        )
        assert api_key.key == test_api_key.key
        assert api_key.name == "pytest_test_key"

    def test_delete_api_key(self, live_client: VergeClient) -> None:
        """Test deleting an API key."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_delete_test",
        )

        # Delete
        live_client.api_keys.delete(result.key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.api_keys.get(result.key)

    def test_delete_via_object_method(self, live_client: VergeClient) -> None:
        """Test deleting via APIKey.delete() method."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_obj_delete_test",
        )

        # Get the API key object
        api_key = live_client.api_keys.get(result.key)

        # Delete via method
        api_key.delete()

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.api_keys.get(result.key)


@pytest.mark.integration
class TestAPIKeyProperties:
    """Integration tests for API key property access."""

    @pytest.fixture
    def test_api_key(self, live_client: VergeClient):
        """Create a test API key and cleanup afterwards."""
        result = live_client.api_keys.create(
            user="admin",
            name="pytest_props_test",
            description="Property test key",
            expires_in="7d",
            ip_allow_list=["10.0.0.0/8"],
        )
        yield result
        with contextlib.suppress(NotFoundError):
            live_client.api_keys.delete(result.key)

    def test_api_key_basic_properties(self, test_api_key, live_client: VergeClient) -> None:
        """Test accessing basic properties on API key."""
        api_key = live_client.api_keys.get(test_api_key.key)

        assert isinstance(api_key, APIKey)
        assert api_key.key == test_api_key.key
        assert api_key.name == "pytest_props_test"
        assert api_key.description == "Property test key"
        assert api_key.user_key > 0
        assert api_key.user_name == "admin"

    def test_api_key_timestamp_properties(self, test_api_key, live_client: VergeClient) -> None:
        """Test timestamp properties on API key."""
        api_key = live_client.api_keys.get(test_api_key.key)

        # Created should be set
        assert api_key.created is not None
        assert api_key.created_datetime is not None

        # Expires should be set (we created with 7d expiration)
        assert api_key.expires is not None
        assert api_key.expires_datetime is not None
        assert api_key.is_expired is False

        # Last login should be None (never used)
        assert api_key.last_login is None
        assert api_key.last_login_datetime is None

    def test_api_key_ip_list_properties(self, test_api_key, live_client: VergeClient) -> None:
        """Test IP list properties on API key."""
        api_key = live_client.api_keys.get(test_api_key.key)

        assert isinstance(api_key.ip_allow_list, list)
        assert "10.0.0.0/8" in api_key.ip_allow_list

        assert isinstance(api_key.ip_deny_list, list)
