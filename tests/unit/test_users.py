"""Unit tests for system user operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.users import User, UserManager


class TestUser:
    """Tests for User resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        user = User(data, MagicMock())
        assert user.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        user = User({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = user.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "testuser"}
        user = User(data, MagicMock())
        assert user.name == "testuser"

    def test_user_type_property(self) -> None:
        """Test user_type property."""
        data = {"$key": 1, "type": "api"}
        user = User(data, MagicMock())
        assert user.user_type == "api"

    def test_user_type_default(self) -> None:
        """Test user_type property defaults to normal."""
        user = User({"$key": 1}, MagicMock())
        assert user.user_type == "normal"

    def test_user_type_display(self) -> None:
        """Test user_type_display property."""
        test_cases = [
            ("normal", "Normal"),
            ("api", "API"),
            ("vdi", "VDI"),
            ("site_sync", "Site Sync"),
            ("site_user", "Site User"),
            ("unknown", "unknown"),  # Passthrough for unknown types
        ]
        for raw_type, expected_display in test_cases:
            data = {"$key": 1, "type": raw_type}
            user = User(data, MagicMock())
            assert user.user_type_display == expected_display

    def test_displayname_property(self) -> None:
        """Test displayname property."""
        data = {"$key": 1, "displayname": "Test User"}
        user = User(data, MagicMock())
        assert user.displayname == "Test User"

    def test_displayname_none(self) -> None:
        """Test displayname property when not set."""
        user = User({"$key": 1}, MagicMock())
        assert user.displayname is None

    def test_email_property(self) -> None:
        """Test email property."""
        data = {"$key": 1, "email": "test@example.com"}
        user = User(data, MagicMock())
        assert user.email == "test@example.com"

    def test_is_enabled_true(self) -> None:
        """Test is_enabled property when enabled."""
        data = {"$key": 1, "enabled": True}
        user = User(data, MagicMock())
        assert user.is_enabled is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled property when disabled."""
        data = {"$key": 1, "enabled": False}
        user = User(data, MagicMock())
        assert user.is_enabled is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled property defaults to True."""
        user = User({"$key": 1}, MagicMock())
        assert user.is_enabled is True

    def test_created_property(self) -> None:
        """Test created property."""
        data = {"$key": 1, "created": 1700000000}
        user = User(data, MagicMock())
        assert user.created == 1700000000

    def test_created_none(self) -> None:
        """Test created property when not set."""
        user = User({"$key": 1}, MagicMock())
        assert user.created is None

    def test_last_login_property(self) -> None:
        """Test last_login property."""
        data = {"$key": 1, "last_login": 1700000000}
        user = User(data, MagicMock())
        assert user.last_login == 1700000000

    def test_last_login_zero(self) -> None:
        """Test last_login property returns None for zero (never logged in)."""
        data = {"$key": 1, "last_login": 0}
        user = User(data, MagicMock())
        assert user.last_login is None

    def test_change_password_property(self) -> None:
        """Test change_password property."""
        data = {"$key": 1, "change_password": True}
        user = User(data, MagicMock())
        assert user.change_password is True

    def test_change_password_default(self) -> None:
        """Test change_password property defaults to False."""
        user = User({"$key": 1}, MagicMock())
        assert user.change_password is False

    def test_physical_access_property(self) -> None:
        """Test physical_access property."""
        data = {"$key": 1, "physical_access": True}
        user = User(data, MagicMock())
        assert user.physical_access is True

    def test_physical_access_default(self) -> None:
        """Test physical_access property defaults to False."""
        user = User({"$key": 1}, MagicMock())
        assert user.physical_access is False

    def test_two_factor_enabled_property(self) -> None:
        """Test two_factor_enabled property."""
        data = {"$key": 1, "two_factor_authentication": True}
        user = User(data, MagicMock())
        assert user.two_factor_enabled is True

    def test_two_factor_enabled_default(self) -> None:
        """Test two_factor_enabled property defaults to False."""
        user = User({"$key": 1}, MagicMock())
        assert user.two_factor_enabled is False

    def test_two_factor_type_property(self) -> None:
        """Test two_factor_type property."""
        data = {"$key": 1, "two_factor_type": "authenticator"}
        user = User(data, MagicMock())
        assert user.two_factor_type == "authenticator"

    def test_two_factor_type_display(self) -> None:
        """Test two_factor_type_display property."""
        test_cases = [
            ("email", "Email"),
            ("authenticator", "Authenticator (TOTP)"),
            (None, "None"),
        ]
        for raw_type, expected_display in test_cases:
            data: dict[str, Any] = {"$key": 1}
            if raw_type is not None:
                data["two_factor_type"] = raw_type
            user = User(data, MagicMock())
            assert user.two_factor_type_display == expected_display

    def test_account_locked_property(self) -> None:
        """Test account_locked property."""
        data = {"$key": 1, "account_locked": 1700000000}
        user = User(data, MagicMock())
        assert user.account_locked == 1700000000

    def test_account_locked_zero(self) -> None:
        """Test account_locked returns None when zero (not locked)."""
        data = {"$key": 1, "account_locked": 0}
        user = User(data, MagicMock())
        assert user.account_locked is None

    def test_is_locked_true(self) -> None:
        """Test is_locked property when locked."""
        data = {"$key": 1, "account_locked": 1700000000}
        user = User(data, MagicMock())
        assert user.is_locked is True

    def test_is_locked_false(self) -> None:
        """Test is_locked property when not locked."""
        data = {"$key": 1, "account_locked": 0}
        user = User(data, MagicMock())
        assert user.is_locked is False

    def test_failed_attempts_property(self) -> None:
        """Test failed_attempts property."""
        data = {"$key": 1, "failed_attempts": 3}
        user = User(data, MagicMock())
        assert user.failed_attempts == 3

    def test_failed_attempts_default(self) -> None:
        """Test failed_attempts property defaults to 0."""
        user = User({"$key": 1}, MagicMock())
        assert user.failed_attempts == 0

    def test_auth_source_property(self) -> None:
        """Test auth_source property."""
        data = {"$key": 1, "auth_source": 5}
        user = User(data, MagicMock())
        assert user.auth_source == 5

    def test_auth_source_name_property(self) -> None:
        """Test auth_source_name property."""
        data = {"$key": 1, "auth_source_name": "LDAP"}
        user = User(data, MagicMock())
        assert user.auth_source_name == "LDAP"

    def test_auth_source_name_from_display(self) -> None:
        """Test auth_source_name falls back to auth_source_display."""
        data = {"$key": 1, "auth_source_display": "LDAP"}
        user = User(data, MagicMock())
        assert user.auth_source_name == "LDAP"

    def test_remote_name_property(self) -> None:
        """Test remote_name property."""
        data = {"$key": 1, "remote_name": "user@domain.local"}
        user = User(data, MagicMock())
        assert user.remote_name == "user@domain.local"

    def test_identity_property(self) -> None:
        """Test identity property."""
        data = {"$key": 1, "identity": 10}
        user = User(data, MagicMock())
        assert user.identity == 10

    def test_creator_property(self) -> None:
        """Test creator property."""
        data = {"$key": 1, "creator": "admin"}
        user = User(data, MagicMock())
        assert user.creator == "admin"

    def test_ssh_keys_property(self) -> None:
        """Test ssh_keys property."""
        data = {"$key": 1, "ssh_keys": "ssh-rsa AAAA..."}
        user = User(data, MagicMock())
        assert user.ssh_keys == "ssh-rsa AAAA..."

    def test_enable_method(self) -> None:
        """Test enable method calls manager."""
        manager = MagicMock()
        manager.enable.return_value = User({"$key": 1, "enabled": True}, manager)
        user = User({"$key": 1, "enabled": False}, manager)

        result = user.enable()

        manager.enable.assert_called_once_with(1)
        assert result.is_enabled is True

    def test_disable_method(self) -> None:
        """Test disable method calls manager."""
        manager = MagicMock()
        manager.disable.return_value = User({"$key": 1, "enabled": False}, manager)
        user = User({"$key": 1, "enabled": True}, manager)

        result = user.disable()

        manager.disable.assert_called_once_with(1)
        assert result.is_enabled is False


class TestUserManager:
    """Tests for UserManager."""

    def _create_manager(self) -> tuple[UserManager, MagicMock]:
        """Create a UserManager with mocked client."""
        client = MagicMock()
        manager = UserManager(client)
        return manager, client

    # list() tests

    def test_list_returns_users(self) -> None:
        """Test list returns User objects."""
        manager, client = self._create_manager()
        client._request.return_value = [
            {"$key": 1, "name": "user1", "type": "normal"},
            {"$key": 2, "name": "user2", "type": "api"},
        ]

        result = manager.list()

        assert len(result) == 2
        assert all(isinstance(u, User) for u in result)
        assert result[0].name == "user1"
        assert result[1].name == "user2"

    def test_list_excludes_system_users_by_default(self) -> None:
        """Test list excludes system user types by default."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list()

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "type ne 'site_sync'" in filter_param
        assert "type ne 'site_user'" in filter_param

    def test_list_includes_system_users_when_requested(self) -> None:
        """Test list can include system user types."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(include_system=True)

        call_args = client._request.call_args
        params = call_args.kwargs["params"]
        # Should not have the system type exclusion filter
        assert "filter" not in params or "site_sync" not in params.get("filter", "")

    def test_list_with_user_type_filter(self) -> None:
        """Test list filters by user type."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(user_type="api")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "type eq 'api'" in filter_param

    def test_list_with_enabled_filter_true(self) -> None:
        """Test list filters by enabled=True."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(enabled=True)

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "enabled eq true" in filter_param

    def test_list_with_enabled_filter_false(self) -> None:
        """Test list filters by enabled=False."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(enabled=False)

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "enabled eq false" in filter_param

    def test_list_with_custom_filter(self) -> None:
        """Test list with custom OData filter."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(filter="physical_access eq true")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "physical_access eq true" in filter_param

    def test_list_with_pagination(self) -> None:
        """Test list with limit and offset."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(limit=10, offset=5)

        call_args = client._request.call_args
        params = call_args.kwargs["params"]
        assert params["limit"] == 10
        assert params["offset"] == 5

    def test_list_returns_empty_for_none(self) -> None:
        """Test list returns empty list for None response."""
        manager, client = self._create_manager()
        client._request.return_value = None

        result = manager.list()

        assert result == []

    def test_list_enabled(self) -> None:
        """Test list_enabled convenience method."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "user1", "enabled": True}]

        result = manager.list_enabled()

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "enabled eq true" in filter_param
        assert len(result) == 1

    def test_list_disabled(self) -> None:
        """Test list_disabled convenience method."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "user1", "enabled": False}]

        manager.list_disabled()

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "enabled eq false" in filter_param

    def test_list_api_users(self) -> None:
        """Test list_api_users convenience method."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "apiuser", "type": "api"}]

        manager.list_api_users()

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "type eq 'api'" in filter_param

    def test_list_vdi_users(self) -> None:
        """Test list_vdi_users convenience method."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "vdiuser", "type": "vdi"}]

        manager.list_vdi_users()

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "type eq 'vdi'" in filter_param

    # get() tests

    def test_get_by_key(self) -> None:
        """Test get by key."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "name": "testuser"}

        result = manager.get(1)

        client._request.assert_called_once()
        assert "users/1" in client._request.call_args.args[1]
        assert result.name == "testuser"

    def test_get_by_name(self) -> None:
        """Test get by name."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "testuser"}]

        result = manager.get(name="testuser")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "name eq 'testuser'" in filter_param
        assert result.name == "testuser"

    def test_get_by_name_escapes_quotes(self) -> None:
        """Test get by name escapes single quotes."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "test'user"}]

        manager.get(name="test'user")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "name eq 'test''user'" in filter_param

    def test_get_not_found_by_key(self) -> None:
        """Test get raises NotFoundError when user not found by key."""
        manager, client = self._create_manager()
        client._request.return_value = None

        with pytest.raises(NotFoundError, match="key 999"):
            manager.get(999)

    def test_get_not_found_by_name(self) -> None:
        """Test get raises NotFoundError when user not found by name."""
        manager, client = self._create_manager()
        client._request.return_value = []

        with pytest.raises(NotFoundError, match="'nonexistent'"):
            manager.get(name="nonexistent")

    def test_get_requires_key_or_name(self) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        manager, client = self._create_manager()

        with pytest.raises(ValueError, match="key or name"):
            manager.get()

    # create() tests

    def test_create_basic_user(self) -> None:
        """Test create with required parameters."""
        manager, client = self._create_manager()
        # First call returns created user key, second call fetches user
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser", "type": "normal", "enabled": True},
        ]

        result = manager.create(name="newuser", password="pass123")

        # Verify POST was called
        post_call = client._request.call_args_list[0]
        assert post_call.args[0] == "POST"
        assert post_call.args[1] == "users"
        body = post_call.kwargs["json_data"]
        assert body["name"] == "newuser"
        assert body["password"] == "pass123"
        assert body["type"] == "normal"
        assert body["enabled"] is True

        assert result.name == "newuser"

    def test_create_lowercases_name(self) -> None:
        """Test create converts name to lowercase."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser", "type": "normal"},
        ]

        manager.create(name="NewUser", password="pass123")

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["name"] == "newuser"

    def test_create_with_displayname_and_email(self) -> None:
        """Test create with displayname and email."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(
            name="newuser",
            password="pass123",
            displayname="New User",
            email="NEW@example.com",
        )

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["displayname"] == "New User"
        assert body["email"] == "new@example.com"  # Lowercased

    def test_create_api_user(self) -> None:
        """Test create API user."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "apiuser", "type": "api"},
        ]

        manager.create(name="apiuser", password="pass123", user_type="api")

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["type"] == "api"

    def test_create_with_password_change(self) -> None:
        """Test create with change_password flag."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(name="newuser", password="pass123", change_password=True)

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["change_password"] is True

    def test_create_with_physical_access(self) -> None:
        """Test create with physical_access flag."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(name="newuser", password="pass123", physical_access=True)

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["physical_access"] is True

    def test_create_with_2fa_email(self) -> None:
        """Test create with 2FA email enabled."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(
            name="newuser",
            password="pass123",
            email="user@example.com",
            two_factor_enabled=True,
            two_factor_type="email",
        )

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["two_factor_authentication"] is True
        assert body["two_factor_type"] == "email"

    def test_create_with_2fa_authenticator(self) -> None:
        """Test create with 2FA authenticator enabled."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(
            name="newuser",
            password="pass123",
            email="user@example.com",
            two_factor_enabled=True,
            two_factor_type="authenticator",
        )

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["two_factor_setup_next_login"] is True
        assert body["two_factor_type"] == "authenticator"

    def test_create_2fa_requires_email(self) -> None:
        """Test create with 2FA raises ValueError without email."""
        manager, client = self._create_manager()

        with pytest.raises(ValueError, match="Email address is required"):
            manager.create(name="newuser", password="pass123", two_factor_enabled=True)

    def test_create_with_ssh_keys_list(self) -> None:
        """Test create with SSH keys as list."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(
            name="newuser",
            password="pass123",
            ssh_keys=["ssh-rsa KEY1", "ssh-rsa KEY2"],
        )

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["ssh_keys"] == "ssh-rsa KEY1\nssh-rsa KEY2"

    def test_create_with_ssh_keys_string(self) -> None:
        """Test create with SSH keys as string."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "newuser"},
        ]

        manager.create(
            name="newuser",
            password="pass123",
            ssh_keys="ssh-rsa MYKEY",
        )

        post_call = client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["ssh_keys"] == "ssh-rsa MYKEY"

    # update() tests

    def test_update_password(self) -> None:
        """Test update password."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "testuser"},  # GET response
        ]

        manager.update(1, password="newpass123")

        put_call = client._request.call_args_list[0]
        assert put_call.args[0] == "PUT"
        body = put_call.kwargs["json_data"]
        assert body["password"] == "newpass123"

    def test_update_displayname(self) -> None:
        """Test update displayname."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser", "displayname": "New Name"},
        ]

        result = manager.update(1, displayname="New Name")

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["displayname"] == "New Name"
        assert result.displayname == "New Name"

    def test_update_email(self) -> None:
        """Test update email (lowercases)."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, email="NEW@Example.com")

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["email"] == "new@example.com"

    def test_update_enabled(self) -> None:
        """Test update enabled status."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser", "enabled": False},
        ]

        result = manager.update(1, enabled=False)

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["enabled"] is False
        assert result.is_enabled is False

    def test_update_change_password(self) -> None:
        """Test update change_password flag."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, change_password=True)

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["change_password"] is True

    def test_update_physical_access(self) -> None:
        """Test update physical_access flag."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, physical_access=True)

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["physical_access"] is True

    def test_update_two_factor(self) -> None:
        """Test update 2FA settings."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, two_factor_enabled=True, two_factor_type="authenticator")

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["two_factor_authentication"] is True
        assert body["two_factor_type"] == "authenticator"

    def test_update_ssh_keys_list(self) -> None:
        """Test update SSH keys with list."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, ssh_keys=["ssh-rsa KEY1", "ssh-rsa KEY2"])

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["ssh_keys"] == "ssh-rsa KEY1\nssh-rsa KEY2"

    def test_update_ssh_keys_clear(self) -> None:
        """Test update SSH keys with empty string clears them."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser"},
        ]

        manager.update(1, ssh_keys="")

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["ssh_keys"] == ""

    def test_update_no_changes(self) -> None:
        """Test update with no changes just returns user."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "name": "testuser"}

        manager.update(1)

        # Should only call GET, not PUT
        assert client._request.call_count == 1
        get_call = client._request.call_args
        assert "users/1" in get_call.args[1]

    # enable() and disable() tests

    def test_enable_user(self) -> None:
        """Test enable user."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser", "enabled": True},
        ]

        result = manager.enable(1)

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["enabled"] is True
        assert result.is_enabled is True

    def test_disable_user(self) -> None:
        """Test disable user."""
        manager, client = self._create_manager()
        client._request.side_effect = [
            None,
            {"$key": 1, "name": "testuser", "enabled": False},
        ]

        result = manager.disable(1)

        put_call = client._request.call_args_list[0]
        body = put_call.kwargs["json_data"]
        assert body["enabled"] is False
        assert result.is_enabled is False

    # delete() tests

    def test_delete_user(self) -> None:
        """Test delete user."""
        manager, client = self._create_manager()
        client._request.return_value = None

        manager.delete(1)

        client._request.assert_called_once_with("DELETE", "users/1")
