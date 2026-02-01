"""Integration tests for OIDC application operations."""

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.oidc_applications import OidcApplication


@pytest.mark.integration
class TestOidcApplicationOperations:
    """Integration tests for OIDC application operations against live VergeOS."""

    def test_list_oidc_applications(self, live_client: VergeClient) -> None:
        """Test listing OIDC applications."""
        applications = live_client.oidc_applications.list()
        assert isinstance(applications, list)

        # If applications exist, verify structure
        if len(applications) > 0:
            app = applications[0]
            assert "$key" in app
            assert "name" in app

    def test_list_oidc_applications_enabled_filter(self, live_client: VergeClient) -> None:
        """Test listing OIDC applications filtered by enabled status."""
        enabled_apps = live_client.oidc_applications.list(enabled=True)
        assert isinstance(enabled_apps, list)

        # All returned apps should be enabled
        for app in enabled_apps:
            assert app.is_enabled is True

    def test_get_oidc_application_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent OIDC application."""
        with pytest.raises(NotFoundError):
            live_client.oidc_applications.get(999999)

    def test_get_oidc_application_by_name_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent OIDC application by name."""
        with pytest.raises(NotFoundError):
            live_client.oidc_applications.get(name="NonexistentOidcApp12345")


@pytest.mark.integration
class TestOidcApplicationCRUD:
    """Integration tests for OIDC application CRUD operations."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application for CRUD tests and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_test_oidc_app",
            redirect_uri="https://pytest.example.com/callback",
            description="PyTest integration test OIDC app",
        )
        yield app
        # Cleanup
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_create_oidc_application(self, live_client: VergeClient) -> None:
        """Test creating an OIDC application."""
        app = live_client.oidc_applications.create(
            name="pytest_create_test_oidc",
            redirect_uri="https://pytest-create.example.com/callback",
            description="Created by pytest",
        )

        try:
            assert isinstance(app, OidcApplication)
            assert app.name == "pytest_create_test_oidc"
            assert app.is_enabled is True

            # Should have auto-generated credentials
            assert app.client_id is not None
            assert len(app.client_id) > 0
            assert app.client_secret is not None
            assert len(app.client_secret) > 0

            # Verify redirect URIs
            assert "https://pytest-create.example.com/callback" in app.redirect_uris

            # Verify application exists
            retrieved = live_client.oidc_applications.get(app.key)
            assert retrieved.name == "pytest_create_test_oidc"
        finally:
            live_client.oidc_applications.delete(app.key)

    def test_create_oidc_application_multiple_redirects(self, live_client: VergeClient) -> None:
        """Test creating an OIDC application with multiple redirect URIs."""
        app = live_client.oidc_applications.create(
            name="pytest_multi_redirect_oidc",
            redirect_uri=[
                "https://app1.example.com/callback",
                "https://app2.example.com/callback",
                "https://staging.example.com/callback",
            ],
        )

        try:
            uris = app.redirect_uris
            assert len(uris) == 3
            assert "https://app1.example.com/callback" in uris
            assert "https://app2.example.com/callback" in uris
            assert "https://staging.example.com/callback" in uris
        finally:
            live_client.oidc_applications.delete(app.key)

    def test_create_oidc_application_with_scopes(self, live_client: VergeClient) -> None:
        """Test creating an OIDC application with custom scopes."""
        app = live_client.oidc_applications.create(
            name="pytest_scopes_oidc",
            redirect_uri="https://pytest-scopes.example.com/callback",
            scope_profile=True,
            scope_email=True,
            scope_groups=False,
        )

        try:
            scopes = app.scopes
            assert "openid" in scopes  # Always included
            assert "profile" in scopes
            assert "email" in scopes
            assert "groups" not in scopes
        finally:
            live_client.oidc_applications.delete(app.key)

    def test_get_oidc_application_by_key(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test getting an OIDC application by key."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        assert app.key == test_oidc_app.key
        assert app.name == "pytest_test_oidc_app"

    def test_get_oidc_application_by_name(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test getting an OIDC application by name."""
        app = live_client.oidc_applications.get(name="pytest_test_oidc_app")
        assert app.key == test_oidc_app.key
        assert app.name == "pytest_test_oidc_app"

    def test_get_oidc_application_with_secret(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test getting an OIDC application with client secret."""
        # Without include_secret, secret may be None
        app = live_client.oidc_applications.get(test_oidc_app.key, include_secret=True)
        assert app.client_secret is not None
        assert len(app.client_secret) > 0

    def test_get_oidc_application_with_well_known(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test getting an OIDC application with well-known configuration."""
        app = live_client.oidc_applications.get(test_oidc_app.key, include_well_known=True)
        # well_known_configuration may or may not be set depending on config
        # Just verify we can access it
        _ = app.well_known_configuration

    def test_update_oidc_application(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test updating an OIDC application."""
        updated = live_client.oidc_applications.update(
            test_oidc_app.key,
            name="pytest_updated_oidc_app",
            description="Updated by pytest",
        )

        assert updated.name == "pytest_updated_oidc_app"
        assert updated.description == "Updated by pytest"

        # Verify change persisted
        retrieved = live_client.oidc_applications.get(test_oidc_app.key)
        assert retrieved.name == "pytest_updated_oidc_app"

    def test_update_oidc_application_redirect_uri(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test updating OIDC application redirect URIs."""
        updated = live_client.oidc_applications.update(
            test_oidc_app.key,
            redirect_uri="https://new-redirect.example.com/callback",
        )

        assert "https://new-redirect.example.com/callback" in updated.redirect_uris

    def test_delete_oidc_application(self, live_client: VergeClient) -> None:
        """Test deleting an OIDC application."""
        app = live_client.oidc_applications.create(
            name="pytest_delete_test_oidc",
            redirect_uri="https://pytest-delete.example.com/callback",
        )

        # Delete
        live_client.oidc_applications.delete(app.key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.oidc_applications.get(app.key)

    def test_delete_via_object_method(self, live_client: VergeClient) -> None:
        """Test deleting via OidcApplication.delete() method."""
        app = live_client.oidc_applications.create(
            name="pytest_obj_delete_oidc",
            redirect_uri="https://pytest-objdel.example.com/callback",
        )

        # Delete via method
        app.delete()

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.oidc_applications.get(app.key)


@pytest.mark.integration
class TestOidcApplicationProperties:
    """Integration tests for OIDC application property access."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_props_test_oidc",
            redirect_uri=[
                "https://prop-test1.example.com/callback",
                "https://prop-test2.example.com/callback",
            ],
            description="Property test OIDC app",
            scope_profile=True,
            scope_email=True,
            scope_groups=True,
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_oidc_application_basic_properties(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test accessing basic properties on OIDC application."""
        app = live_client.oidc_applications.get(test_oidc_app.key)

        assert isinstance(app, OidcApplication)
        assert app.key == test_oidc_app.key
        assert app.name == "pytest_props_test_oidc"
        assert app.description == "Property test OIDC app"
        assert app.is_enabled is True

    def test_oidc_application_client_credentials(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test client credentials on OIDC application."""
        app = live_client.oidc_applications.get(test_oidc_app.key, include_secret=True)

        assert app.client_id is not None
        assert len(app.client_id) > 0
        assert app.client_secret is not None
        assert len(app.client_secret) > 0

    def test_oidc_application_redirect_uris(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test redirect URIs property."""
        app = live_client.oidc_applications.get(test_oidc_app.key)

        uris = app.redirect_uris
        assert isinstance(uris, list)
        assert len(uris) == 2
        assert "https://prop-test1.example.com/callback" in uris
        assert "https://prop-test2.example.com/callback" in uris

    def test_oidc_application_scopes(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test scopes property."""
        app = live_client.oidc_applications.get(test_oidc_app.key)

        scopes = app.scopes
        assert isinstance(scopes, list)
        assert "openid" in scopes
        assert "profile" in scopes
        assert "email" in scopes
        assert "groups" in scopes


@pytest.mark.integration
class TestOidcApplicationEnableDisable:
    """Integration tests for OIDC application enable/disable."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_enable_test_oidc",
            redirect_uri="https://enable-test.example.com/callback",
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_disable_oidc_application(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test disabling an OIDC application."""
        # Verify initially enabled
        app = live_client.oidc_applications.get(test_oidc_app.key)
        assert app.is_enabled is True

        # Disable
        updated = app.disable()
        assert updated.is_enabled is False

        # Verify persisted
        retrieved = live_client.oidc_applications.get(test_oidc_app.key)
        assert retrieved.is_enabled is False

    def test_enable_oidc_application(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test enabling an OIDC application."""
        # Disable first
        app = live_client.oidc_applications.get(test_oidc_app.key)
        app.disable()

        # Enable
        updated = app.enable()
        assert updated.is_enabled is True

        # Verify persisted
        retrieved = live_client.oidc_applications.get(test_oidc_app.key)
        assert retrieved.is_enabled is True

    def test_update_enabled_via_manager(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test updating enabled state via manager."""
        # Disable via manager
        updated = live_client.oidc_applications.update(test_oidc_app.key, enabled=False)
        assert updated.is_enabled is False

        # Enable via manager
        updated = live_client.oidc_applications.update(test_oidc_app.key, enabled=True)
        assert updated.is_enabled is True


@pytest.mark.integration
class TestOidcApplicationAccessControl:
    """Integration tests for OIDC application access control."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application with access restriction."""
        app = live_client.oidc_applications.create(
            name="pytest_acl_test_oidc",
            redirect_uri="https://acl-test.example.com/callback",
            restrict_access=True,
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_oidc_application_restrict_access(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test that access restriction is enabled."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        assert app.is_access_restricted is True

    def test_list_allowed_users_empty(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test listing allowed users (initially empty)."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        users = app.allowed_users.list()
        assert isinstance(users, list)
        assert len(users) == 0

    def test_list_allowed_groups_empty(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test listing allowed groups (initially empty)."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        groups = app.allowed_groups.list()
        assert isinstance(groups, list)
        assert len(groups) == 0

    def test_add_and_remove_allowed_user(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test adding and removing an allowed user."""
        # Get admin user
        admin = live_client.users.get(name="admin")

        # Add user to allowed list
        app = live_client.oidc_applications.get(test_oidc_app.key)
        entry = app.allowed_users.add(user_key=admin.key)

        try:
            assert entry.user_key == admin.key

            # Verify user in list
            users = app.allowed_users.list()
            assert len(users) == 1
            assert users[0].user_key == admin.key
        finally:
            # Remove user
            entry.delete()

        # Verify removed
        users = app.allowed_users.list()
        assert len(users) == 0

    def test_add_and_remove_allowed_group(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test adding and removing an allowed group."""
        # Get groups
        groups = live_client.groups.list(limit=1)
        if len(groups) == 0:
            pytest.skip("No groups exist to test with")

        test_group = groups[0]

        # Add group to allowed list
        app = live_client.oidc_applications.get(test_oidc_app.key)
        entry = app.allowed_groups.add(group_key=test_group.key)

        try:
            assert entry.group_key == test_group.key

            # Verify group in list
            allowed = app.allowed_groups.list()
            assert len(allowed) == 1
            assert allowed[0].group_key == test_group.key
        finally:
            # Remove group
            entry.delete()

        # Verify removed
        allowed = app.allowed_groups.list()
        assert len(allowed) == 0


@pytest.mark.integration
class TestOidcApplicationLogs:
    """Integration tests for OIDC application log operations."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_log_test_oidc",
            redirect_uri="https://log-test.example.com/callback",
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_list_application_logs(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test listing application logs."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        logs = app.logs.list()
        assert isinstance(logs, list)

    def test_list_application_logs_via_manager(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test listing application logs via manager."""
        logs_mgr = live_client.oidc_applications.logs(test_oidc_app.key)
        logs = logs_mgr.list()
        assert isinstance(logs, list)

    def test_list_errors_method(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test list_errors convenience method."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        errors = app.logs.list_errors()
        assert isinstance(errors, list)

    def test_list_warnings_method(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test list_warnings convenience method."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        warnings = app.logs.list_warnings()
        assert isinstance(warnings, list)

    def test_list_audits_method(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test list_audits convenience method."""
        app = live_client.oidc_applications.get(test_oidc_app.key)
        audits = app.logs.list_audits()
        assert isinstance(audits, list)


@pytest.mark.integration
class TestOidcApplicationRefresh:
    """Integration tests for OIDC application refresh functionality."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_refresh_test_oidc",
            redirect_uri="https://refresh-test.example.com/callback",
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_refresh_oidc_application(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test refreshing an OIDC application."""
        # Update via manager
        live_client.oidc_applications.update(test_oidc_app.key, name="pytest_refreshed_oidc_name")

        # Original object still has old name
        assert test_oidc_app.name == "pytest_refresh_test_oidc"

        # Refresh to get new data
        refreshed = test_oidc_app.refresh()
        assert refreshed.name == "pytest_refreshed_oidc_name"

    def test_save_oidc_application(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test saving changes via object method."""
        updated = test_oidc_app.save(
            name="pytest_saved_oidc_name",
            description="Saved via object method",
        )
        assert updated.name == "pytest_saved_oidc_name"
        assert updated.description == "Saved via object method"

        # Verify persisted
        retrieved = live_client.oidc_applications.get(test_oidc_app.key)
        assert retrieved.name == "pytest_saved_oidc_name"


@pytest.mark.integration
class TestOidcApplicationScopedManagers:
    """Integration tests for scoped manager access patterns."""

    @pytest.fixture
    def test_oidc_app(self, live_client: VergeClient):
        """Create a test OIDC application and cleanup afterwards."""
        app = live_client.oidc_applications.create(
            name="pytest_scoped_mgr_test",
            redirect_uri="https://scoped-test.example.com/callback",
            restrict_access=True,
        )
        yield app
        with contextlib.suppress(NotFoundError):
            live_client.oidc_applications.delete(app.key)

    def test_allowed_users_via_manager_method(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test getting allowed users manager via manager method."""
        mgr = live_client.oidc_applications.allowed_users(test_oidc_app.key)
        users = mgr.list()
        assert isinstance(users, list)

    def test_allowed_groups_via_manager_method(
        self, test_oidc_app, live_client: VergeClient
    ) -> None:
        """Test getting allowed groups manager via manager method."""
        mgr = live_client.oidc_applications.allowed_groups(test_oidc_app.key)
        groups = mgr.list()
        assert isinstance(groups, list)

    def test_logs_via_manager_method(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test getting logs manager via manager method."""
        mgr = live_client.oidc_applications.logs(test_oidc_app.key)
        logs = mgr.list()
        assert isinstance(logs, list)

    def test_global_user_manager_filtering(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test filtering global user manager by application."""
        # Use global manager with filter
        users = live_client.oidc_application_users.list(oidc_application=test_oidc_app.key)
        assert isinstance(users, list)

    def test_global_group_manager_filtering(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test filtering global group manager by application."""
        # Use global manager with filter
        groups = live_client.oidc_application_groups.list(oidc_application=test_oidc_app.key)
        assert isinstance(groups, list)

    def test_global_log_manager_filtering(self, test_oidc_app, live_client: VergeClient) -> None:
        """Test filtering global log manager by application."""
        # Use global manager with filter
        logs = live_client.oidc_application_logs.list(oidc_application=test_oidc_app.key)
        assert isinstance(logs, list)
