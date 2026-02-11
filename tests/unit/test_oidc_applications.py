"""Unit tests for OIDC application resources."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.client import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.oidc_applications import (
    OidcApplication,
    OidcApplicationGroup,
    OidcApplicationGroupManager,
    OidcApplicationLog,
    OidcApplicationLogManager,
    OidcApplicationManager,
    OidcApplicationUser,
    OidcApplicationUserManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client.is_connected = True
    return client


# =============================================================================
# OidcApplicationUserManager Tests
# =============================================================================


class TestOidcApplicationUserManager:
    """Tests for OidcApplicationUserManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = OidcApplicationUserManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "oidc_application_users"
        assert manager._application_key is None

    def test_init_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager initialization."""
        manager = OidcApplicationUserManager(mock_client, application_key=1)
        assert manager._application_key == 1

    def test_list_returns_users(self, mock_client: MagicMock) -> None:
        """Test listing users."""
        mock_client._request.return_value = [
            {"$key": 1, "oidc_application": 1, "user": 10, "user_display": "admin"},
            {"$key": 2, "oidc_application": 1, "user": 20, "user_display": "user1"},
        ]

        manager = OidcApplicationUserManager(mock_client)
        users = manager.list()

        assert len(users) == 2
        assert isinstance(users[0], OidcApplicationUser)
        assert users[0]["user_display"] == "admin"

    def test_list_with_application_filter(self, mock_client: MagicMock) -> None:
        """Test listing with application filter."""
        mock_client._request.return_value = []

        manager = OidcApplicationUserManager(mock_client)
        manager.list(oidc_application=5)

        call_args = mock_client._request.call_args
        assert "oidc_application eq 5" in call_args[1]["params"]["filter"]

    def test_list_scoped_filters_by_application(self, mock_client: MagicMock) -> None:
        """Test scoped manager auto-filters by application."""
        mock_client._request.return_value = []

        manager = OidcApplicationUserManager(mock_client, application_key=3)
        manager.list()

        call_args = mock_client._request.call_args
        assert "oidc_application eq 3" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting user ACL entry by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "oidc_application": 1,
            "user": 10,
        }

        manager = OidcApplicationUserManager(mock_client)
        entry = manager.get(key=1)

        assert isinstance(entry, OidcApplicationUser)
        assert entry.key == 1

    def test_get_requires_key(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without key."""
        manager = OidcApplicationUserManager(mock_client)
        with pytest.raises(ValueError, match="Key must be provided"):
            manager.get()

    def test_add_user(self, mock_client: MagicMock) -> None:
        """Test adding a user."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "oidc_application": 1, "user": 10},  # GET response
        ]

        manager = OidcApplicationUserManager(mock_client, application_key=1)
        entry = manager.add(user_key=10)

        assert entry.key == 1
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "oidc_application_users")
        body = post_call[1]["json_data"]
        assert body["oidc_application"] == 1
        assert body["user"] == 10

    def test_add_requires_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test add raises ValueError without scoped manager."""
        manager = OidcApplicationUserManager(mock_client)
        with pytest.raises(ValueError, match="Manager must be scoped"):
            manager.add(user_key=10)

    def test_delete_user(self, mock_client: MagicMock) -> None:
        """Test deleting a user ACL entry."""
        mock_client._request.return_value = None

        manager = OidcApplicationUserManager(mock_client)
        manager.delete(key=1)

        mock_client._request.assert_called_once_with("DELETE", "oidc_application_users/1")


class TestOidcApplicationUser:
    """Tests for OidcApplicationUser resource object."""

    def test_application_key_property(self, mock_client: MagicMock) -> None:
        """Test application_key property."""
        manager = OidcApplicationUserManager(mock_client)
        entry = OidcApplicationUser({"oidc_application": 5}, manager)

        assert entry.application_key == 5

    def test_user_key_property(self, mock_client: MagicMock) -> None:
        """Test user_key property."""
        manager = OidcApplicationUserManager(mock_client)
        entry = OidcApplicationUser({"user": 10}, manager)

        assert entry.user_key == 10

    def test_user_display_property(self, mock_client: MagicMock) -> None:
        """Test user_display property."""
        manager = OidcApplicationUserManager(mock_client)
        entry = OidcApplicationUser({"user_display": "admin"}, manager)

        assert entry.user_display == "admin"

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test delete method."""
        mock_client._request.return_value = None

        manager = OidcApplicationUserManager(mock_client)
        entry = OidcApplicationUser({"$key": 1}, manager)
        entry.delete()

        mock_client._request.assert_called_once_with("DELETE", "oidc_application_users/1")


# =============================================================================
# OidcApplicationGroupManager Tests
# =============================================================================


class TestOidcApplicationGroupManager:
    """Tests for OidcApplicationGroupManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = OidcApplicationGroupManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "oidc_application_groups"
        assert manager._application_key is None

    def test_init_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager initialization."""
        manager = OidcApplicationGroupManager(mock_client, application_key=1)
        assert manager._application_key == 1

    def test_list_returns_groups(self, mock_client: MagicMock) -> None:
        """Test listing groups."""
        mock_client._request.return_value = [
            {"$key": 1, "oidc_application": 1, "group": 10, "group_display": "admins"},
            {"$key": 2, "oidc_application": 1, "group": 20, "group_display": "users"},
        ]

        manager = OidcApplicationGroupManager(mock_client)
        groups = manager.list()

        assert len(groups) == 2
        assert isinstance(groups[0], OidcApplicationGroup)
        assert groups[0]["group_display"] == "admins"

    def test_list_scoped_filters_by_application(self, mock_client: MagicMock) -> None:
        """Test scoped manager auto-filters by application."""
        mock_client._request.return_value = []

        manager = OidcApplicationGroupManager(mock_client, application_key=3)
        manager.list()

        call_args = mock_client._request.call_args
        assert "oidc_application eq 3" in call_args[1]["params"]["filter"]

    def test_add_group(self, mock_client: MagicMock) -> None:
        """Test adding a group."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "oidc_application": 1, "group": 10},  # GET response
        ]

        manager = OidcApplicationGroupManager(mock_client, application_key=1)
        entry = manager.add(group_key=10)

        assert entry.key == 1
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["oidc_application"] == 1
        assert body["group"] == 10

    def test_add_requires_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test add raises ValueError without scoped manager."""
        manager = OidcApplicationGroupManager(mock_client)
        with pytest.raises(ValueError, match="Manager must be scoped"):
            manager.add(group_key=10)


class TestOidcApplicationGroup:
    """Tests for OidcApplicationGroup resource object."""

    def test_application_key_property(self, mock_client: MagicMock) -> None:
        """Test application_key property."""
        manager = OidcApplicationGroupManager(mock_client)
        entry = OidcApplicationGroup({"oidc_application": 5}, manager)

        assert entry.application_key == 5

    def test_group_key_property(self, mock_client: MagicMock) -> None:
        """Test group_key property."""
        manager = OidcApplicationGroupManager(mock_client)
        entry = OidcApplicationGroup({"group": 10}, manager)

        assert entry.group_key == 10

    def test_group_display_property(self, mock_client: MagicMock) -> None:
        """Test group_display property."""
        manager = OidcApplicationGroupManager(mock_client)
        entry = OidcApplicationGroup({"group_display": "admins"}, manager)

        assert entry.group_display == "admins"


# =============================================================================
# OidcApplicationLogManager Tests
# =============================================================================


class TestOidcApplicationLogManager:
    """Tests for OidcApplicationLogManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = OidcApplicationLogManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "oidc_application_logs"
        assert manager._application_key is None

    def test_init_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager initialization."""
        manager = OidcApplicationLogManager(mock_client, application_key=1)
        assert manager._application_key == 1

    def test_list_returns_logs(self, mock_client: MagicMock) -> None:
        """Test listing logs."""
        mock_client._request.return_value = [
            {"$key": 1, "level": "audit", "text": "Created"},
            {"$key": 2, "level": "error", "text": "Failed"},
        ]

        manager = OidcApplicationLogManager(mock_client)
        logs = manager.list()

        assert len(logs) == 2
        assert isinstance(logs[0], OidcApplicationLog)

    def test_list_with_level_filter(self, mock_client: MagicMock) -> None:
        """Test listing with level filter."""
        mock_client._request.return_value = []

        manager = OidcApplicationLogManager(mock_client)
        manager.list(level="error")

        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_errors(self, mock_client: MagicMock) -> None:
        """Test list_errors helper."""
        mock_client._request.return_value = []

        manager = OidcApplicationLogManager(mock_client)
        manager.list_errors()

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "level eq 'error'" in filter_str or "level eq 'critical'" in filter_str

    def test_list_warnings(self, mock_client: MagicMock) -> None:
        """Test list_warnings helper."""
        mock_client._request.return_value = []

        manager = OidcApplicationLogManager(mock_client)
        manager.list_warnings()

        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]

    def test_list_audits(self, mock_client: MagicMock) -> None:
        """Test list_audits helper."""
        mock_client._request.return_value = []

        manager = OidcApplicationLogManager(mock_client)
        manager.list_audits()

        call_args = mock_client._request.call_args
        assert "level eq 'audit'" in call_args[1]["params"]["filter"]


class TestOidcApplicationLog:
    """Tests for OidcApplicationLog resource object."""

    def test_application_key_property(self, mock_client: MagicMock) -> None:
        """Test application_key property."""
        manager = OidcApplicationLogManager(mock_client)
        log = OidcApplicationLog({"oidc_application": 5}, manager)

        assert log.application_key == 5

    def test_is_error(self, mock_client: MagicMock) -> None:
        """Test is_error property."""
        manager = OidcApplicationLogManager(mock_client)

        log1 = OidcApplicationLog({"level": "error"}, manager)
        assert log1.is_error is True

        log2 = OidcApplicationLog({"level": "critical"}, manager)
        assert log2.is_error is True

        log3 = OidcApplicationLog({"level": "warning"}, manager)
        assert log3.is_error is False

    def test_is_warning(self, mock_client: MagicMock) -> None:
        """Test is_warning property."""
        manager = OidcApplicationLogManager(mock_client)

        log1 = OidcApplicationLog({"level": "warning"}, manager)
        assert log1.is_warning is True

        log2 = OidcApplicationLog({"level": "error"}, manager)
        assert log2.is_warning is False

    def test_is_audit(self, mock_client: MagicMock) -> None:
        """Test is_audit property."""
        manager = OidcApplicationLogManager(mock_client)

        log1 = OidcApplicationLog({"level": "audit"}, manager)
        assert log1.is_audit is True

        log2 = OidcApplicationLog({"level": "message"}, manager)
        assert log2.is_audit is False


# =============================================================================
# OidcApplicationManager Tests
# =============================================================================


class TestOidcApplicationManager:
    """Tests for OidcApplicationManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = OidcApplicationManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "oidc_applications"

    def test_list_returns_applications(self, mock_client: MagicMock) -> None:
        """Test listing applications."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Tenant Portal", "enabled": True},
            {"$key": 2, "name": "Partner Portal", "enabled": True},
        ]

        manager = OidcApplicationManager(mock_client)
        apps = manager.list()

        assert len(apps) == 2
        assert isinstance(apps[0], OidcApplication)
        assert apps[0]["name"] == "Tenant Portal"

    def test_list_with_enabled_filter(self, mock_client: MagicMock) -> None:
        """Test listing with enabled filter."""
        mock_client._request.return_value = []

        manager = OidcApplicationManager(mock_client)
        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq 1" in call_args[1]["params"]["filter"]

    def test_list_returns_empty_on_none(self, mock_client: MagicMock) -> None:
        """Test listing returns empty list on None response."""
        mock_client._request.return_value = None

        manager = OidcApplicationManager(mock_client)
        apps = manager.list()

        assert apps == []

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting application by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Tenant Portal",
            "client_id": "abc123",
        }

        manager = OidcApplicationManager(mock_client)
        app = manager.get(key=1)

        assert isinstance(app, OidcApplication)
        assert app.key == 1
        assert app["name"] == "Tenant Portal"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting application by name."""
        mock_client._request.return_value = [
            {"$key": 2, "name": "Partner Portal"},
        ]

        manager = OidcApplicationManager(mock_client)
        app = manager.get(name="Partner Portal")

        assert app["name"] == "Partner Portal"

    def test_get_with_include_secret(self, mock_client: MagicMock) -> None:
        """Test get with include_secret includes client_secret field."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Test",
            "client_secret": "secret123",
        }

        manager = OidcApplicationManager(mock_client)
        manager.get(key=1, include_secret=True)

        call_args = mock_client._request.call_args
        assert "client_secret" in call_args[1]["params"]["fields"]

    def test_get_with_include_well_known(self, mock_client: MagicMock) -> None:
        """Test get with include_well_known includes well_known_configuration."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Test",
            "well_known_configuration": "https://example.com/.well-known/openid-configuration",
        }

        manager = OidcApplicationManager(mock_client)
        manager.get(key=1, include_well_known=True)

        call_args = mock_client._request.call_args
        assert "well_known_configuration" in call_args[1]["params"]["fields"]

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = OidcApplicationManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_requires_identifier(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without identifier."""
        manager = OidcApplicationManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_create_application(self, mock_client: MagicMock) -> None:
        """Test creating an application."""
        mock_client._request.side_effect = [
            {"$key": 3},  # POST response
            {"$key": 3, "name": "Test", "client_id": "abc", "client_secret": "xyz"},  # GET
        ]

        manager = OidcApplicationManager(mock_client)
        app = manager.create(
            name="Test",
            redirect_uri="https://example.com/callback",
            description="Test app",
        )

        assert app.key == 3
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "oidc_applications")
        body = post_call[1]["json_data"]
        assert body["name"] == "Test"
        assert body["redirect_uri"] == "https://example.com/callback"
        assert body["description"] == "Test app"
        # force_auth_source and map_user always included (default 0)
        assert body["force_auth_source"] == 0
        assert body["map_user"] == 0

    def test_create_with_list_redirect_uri(self, mock_client: MagicMock) -> None:
        """Test creating with list of redirect URIs."""
        mock_client._request.side_effect = [
            {"$key": 3},
            {"$key": 3, "name": "Test"},
        ]

        manager = OidcApplicationManager(mock_client)
        manager.create(
            name="Test",
            redirect_uri=[
                "https://example.com/callback",
                "https://staging.example.com/callback",
            ],
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        expected = "https://example.com/callback\nhttps://staging.example.com/callback"
        assert body["redirect_uri"] == expected

    def test_create_with_scopes(self, mock_client: MagicMock) -> None:
        """Test creating with scope settings."""
        mock_client._request.side_effect = [
            {"$key": 3},
            {"$key": 3, "name": "Test"},
        ]

        manager = OidcApplicationManager(mock_client)
        manager.create(
            name="Test",
            scope_profile=True,
            scope_email=True,
            scope_groups=False,
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["scope_profile"] is True
        assert body["scope_email"] is True
        assert body["scope_groups"] is False

    def test_create_with_restrict_access(self, mock_client: MagicMock) -> None:
        """Test creating with access restriction."""
        mock_client._request.side_effect = [
            {"$key": 3},
            {"$key": 3, "name": "Test", "restrict_access": True},
        ]

        manager = OidcApplicationManager(mock_client)
        manager.create(
            name="Test",
            restrict_access=True,
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["restrict_access"] is True

    def test_update_application(self, mock_client: MagicMock) -> None:
        """Test updating an application."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated"},  # GET response
        ]

        manager = OidcApplicationManager(mock_client)
        manager.update(key=1, name="Updated", enabled=False)

        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "oidc_applications/1")
        body = put_call[1]["json_data"]
        assert body["name"] == "Updated"
        assert body["enabled"] is False

    def test_update_redirect_uri_list(self, mock_client: MagicMock) -> None:
        """Test updating with list of redirect URIs."""
        mock_client._request.side_effect = [
            None,
            {"$key": 1},
        ]

        manager = OidcApplicationManager(mock_client)
        manager.update(
            key=1,
            redirect_uri=["https://new.example.com/callback"],
        )

        put_call = mock_client._request.call_args_list[0]
        body = put_call[1]["json_data"]
        assert body["redirect_uri"] == "https://new.example.com/callback"

    def test_update_no_changes(self, mock_client: MagicMock) -> None:
        """Test update with no changes returns current app."""
        mock_client._request.return_value = {"$key": 1, "name": "Test"}

        manager = OidcApplicationManager(mock_client)
        manager.update(key=1)

        mock_client._request.assert_called_once()
        assert mock_client._request.call_args[0][0] == "GET"

    def test_delete_application(self, mock_client: MagicMock) -> None:
        """Test deleting an application."""
        mock_client._request.return_value = None

        manager = OidcApplicationManager(mock_client)
        manager.delete(key=1)

        mock_client._request.assert_called_once_with("DELETE", "oidc_applications/1")

    def test_allowed_users_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test allowed_users returns scoped OidcApplicationUserManager."""
        manager = OidcApplicationManager(mock_client)
        user_mgr = manager.allowed_users(key=5)

        assert isinstance(user_mgr, OidcApplicationUserManager)
        assert user_mgr._application_key == 5

    def test_allowed_groups_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test allowed_groups returns scoped OidcApplicationGroupManager."""
        manager = OidcApplicationManager(mock_client)
        group_mgr = manager.allowed_groups(key=5)

        assert isinstance(group_mgr, OidcApplicationGroupManager)
        assert group_mgr._application_key == 5

    def test_logs_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test logs returns scoped OidcApplicationLogManager."""
        manager = OidcApplicationManager(mock_client)
        log_mgr = manager.logs(key=5)

        assert isinstance(log_mgr, OidcApplicationLogManager)
        assert log_mgr._application_key == 5


class TestOidcApplication:
    """Tests for OidcApplication resource object."""

    def test_client_id_property(self, mock_client: MagicMock) -> None:
        """Test client_id property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"client_id": "abc123"}, manager)

        assert app.client_id == "abc123"

    def test_client_secret_property(self, mock_client: MagicMock) -> None:
        """Test client_secret property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"client_secret": "xyz789"}, manager)

        assert app.client_secret == "xyz789"

    def test_is_enabled(self, mock_client: MagicMock) -> None:
        """Test is_enabled property."""
        manager = OidcApplicationManager(mock_client)

        app1 = OidcApplication({"enabled": True}, manager)
        assert app1.is_enabled is True

        app2 = OidcApplication({"enabled": False}, manager)
        assert app2.is_enabled is False

    def test_is_access_restricted(self, mock_client: MagicMock) -> None:
        """Test is_access_restricted property."""
        manager = OidcApplicationManager(mock_client)

        app1 = OidcApplication({"restrict_access": True}, manager)
        assert app1.is_access_restricted is True

        app2 = OidcApplication({"restrict_access": False}, manager)
        assert app2.is_access_restricted is False

    def test_redirect_uris(self, mock_client: MagicMock) -> None:
        """Test redirect_uris property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication(
            {"redirect_uri": "https://a.com/cb\nhttps://b.com/cb"},
            manager,
        )

        uris = app.redirect_uris
        assert len(uris) == 2
        assert "https://a.com/cb" in uris
        assert "https://b.com/cb" in uris

    def test_redirect_uris_empty(self, mock_client: MagicMock) -> None:
        """Test redirect_uris returns empty list when not set."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({}, manager)

        assert app.redirect_uris == []

    def test_well_known_configuration(self, mock_client: MagicMock) -> None:
        """Test well_known_configuration property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication(
            {"well_known_configuration": "https://example.com/.well-known"},
            manager,
        )

        assert app.well_known_configuration == "https://example.com/.well-known"

    def test_scopes(self, mock_client: MagicMock) -> None:
        """Test scopes property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication(
            {"scope_profile": True, "scope_email": True, "scope_groups": False},
            manager,
        )

        scopes = app.scopes
        assert "openid" in scopes
        assert "profile" in scopes
        assert "email" in scopes
        assert "groups" not in scopes

    def test_scopes_all_enabled(self, mock_client: MagicMock) -> None:
        """Test scopes with all enabled."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication(
            {"scope_profile": True, "scope_email": True, "scope_groups": True},
            manager,
        )

        scopes = app.scopes
        assert len(scopes) == 4
        assert set(scopes) == {"openid", "profile", "email", "groups"}

    def test_force_auth_source_key(self, mock_client: MagicMock) -> None:
        """Test force_auth_source_key property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"force_auth_source": 5}, manager)

        assert app.force_auth_source_key == 5

    def test_map_user_key(self, mock_client: MagicMock) -> None:
        """Test map_user_key property."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"map_user": 10}, manager)

        assert app.map_user_key == 10

    def test_allowed_users_property(self, mock_client: MagicMock) -> None:
        """Test allowed_users property returns scoped manager."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 5}, manager)

        user_mgr = app.allowed_users
        assert isinstance(user_mgr, OidcApplicationUserManager)
        assert user_mgr._application_key == 5

    def test_allowed_groups_property(self, mock_client: MagicMock) -> None:
        """Test allowed_groups property returns scoped manager."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 5}, manager)

        group_mgr = app.allowed_groups
        assert isinstance(group_mgr, OidcApplicationGroupManager)
        assert group_mgr._application_key == 5

    def test_logs_property(self, mock_client: MagicMock) -> None:
        """Test logs property returns scoped manager."""
        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 5}, manager)

        log_mgr = app.logs
        assert isinstance(log_mgr, OidcApplicationLogManager)
        assert log_mgr._application_key == 5

    def test_enable(self, mock_client: MagicMock) -> None:
        """Test enable method."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "enabled": True},  # GET
        ]

        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 1, "enabled": False}, manager)
        result = app.enable()

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is True
        assert result["enabled"] is True

    def test_disable(self, mock_client: MagicMock) -> None:
        """Test disable method."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "enabled": False},  # GET
        ]

        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 1, "enabled": True}, manager)
        result = app.disable()

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False
        assert result["enabled"] is False

    def test_refresh(self, mock_client: MagicMock) -> None:
        """Test refresh reloads from API."""
        mock_client._request.return_value = {"$key": 1, "name": "Updated"}

        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 1, "name": "Old"}, manager)
        refreshed = app.refresh()

        assert refreshed["name"] == "Updated"

    def test_save(self, mock_client: MagicMock) -> None:
        """Test save calls update."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "name": "New Name"},  # GET
        ]

        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 1, "name": "Old"}, manager)
        result = app.save(name="New Name")

        assert result["name"] == "New Name"

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test delete."""
        mock_client._request.return_value = None

        manager = OidcApplicationManager(mock_client)
        app = OidcApplication({"$key": 1}, manager)
        app.delete()

        mock_client._request.assert_called_once_with("DELETE", "oidc_applications/1")
