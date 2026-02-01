"""Integration tests for authentication source operations."""

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.auth_sources import AuthSource


@pytest.mark.integration
class TestAuthSourceOperations:
    """Integration tests for auth source operations against live VergeOS."""

    def test_list_auth_sources(self, live_client: VergeClient) -> None:
        """Test listing authentication sources."""
        auth_sources = live_client.auth_sources.list()
        assert isinstance(auth_sources, list)

        # If sources exist, verify structure
        if len(auth_sources) > 0:
            source = auth_sources[0]
            assert "$key" in source
            assert "name" in source
            assert "driver" in source

    def test_list_auth_sources_by_driver(self, live_client: VergeClient) -> None:
        """Test listing auth sources filtered by driver."""
        # This test works even if no sources exist for the driver
        azure_sources = live_client.auth_sources.list(driver="azure")
        assert isinstance(azure_sources, list)

        # All returned sources should have azure driver
        for source in azure_sources:
            assert source.driver == "azure"

    def test_get_auth_source_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent auth source."""
        with pytest.raises(NotFoundError):
            live_client.auth_sources.get(999999)

    def test_get_auth_source_by_name_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent auth source by name."""
        with pytest.raises(NotFoundError):
            live_client.auth_sources.get(name="NonexistentAuthSource12345")


@pytest.mark.integration
class TestAuthSourceCRUD:
    """Integration tests for auth source CRUD operations."""

    @pytest.fixture
    def test_auth_source(self, live_client: VergeClient):
        """Create a test auth source for CRUD tests and cleanup afterwards."""
        source = live_client.auth_sources.create(
            name="pytest_test_source",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
            },
        )
        yield source
        # Cleanup
        with contextlib.suppress(NotFoundError):
            live_client.auth_sources.delete(source.key)

    def test_create_auth_source(self, live_client: VergeClient) -> None:
        """Test creating an auth source."""
        source = live_client.auth_sources.create(
            name="pytest_create_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
        )

        try:
            assert isinstance(source, AuthSource)
            assert source.name == "pytest_create_test"
            assert source.driver == "openid-well-known"
            assert source.is_openid is True

            # Verify source exists
            retrieved = live_client.auth_sources.get(source.key)
            assert retrieved.name == "pytest_create_test"
        finally:
            live_client.auth_sources.delete(source.key)

    def test_create_auth_source_with_styling(self, live_client: VergeClient) -> None:
        """Test creating an auth source with button styling."""
        source = live_client.auth_sources.create(
            name="pytest_styled_source",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
            button_background_color="#4285F4",
            button_color="#ffffff",
            button_fa_icon="bi-box-arrow-in-right",
        )

        try:
            retrieved = live_client.auth_sources.get(source.key)
            style = retrieved.button_style
            assert style["background_color"] == "#4285F4"
            assert style["text_color"] == "#ffffff"
            assert style["icon"] == "bi-box-arrow-in-right"
        finally:
            live_client.auth_sources.delete(source.key)

    def test_get_auth_source_by_key(self, test_auth_source, live_client: VergeClient) -> None:
        """Test getting an auth source by key."""
        source = live_client.auth_sources.get(test_auth_source.key)
        assert source.key == test_auth_source.key
        assert source.name == "pytest_test_source"

    def test_get_auth_source_by_name(self, test_auth_source, live_client: VergeClient) -> None:
        """Test getting an auth source by name."""
        source = live_client.auth_sources.get(name="pytest_test_source")
        assert source.key == test_auth_source.key
        assert source.name == "pytest_test_source"

    def test_get_auth_source_with_settings(
        self, test_auth_source, live_client: VergeClient
    ) -> None:
        """Test getting an auth source with settings included."""
        source = live_client.auth_sources.get(test_auth_source.key, include_settings=True)
        assert source.settings is not None
        assert isinstance(source.settings, dict)
        # Settings should contain what we created
        assert "client_id" in source.settings

    def test_update_auth_source(self, test_auth_source, live_client: VergeClient) -> None:
        """Test updating an auth source."""
        updated = live_client.auth_sources.update(
            test_auth_source.key,
            name="pytest_updated_source",
        )

        assert updated.name == "pytest_updated_source"

        # Verify change persisted
        retrieved = live_client.auth_sources.get(test_auth_source.key)
        assert retrieved.name == "pytest_updated_source"

    def test_update_auth_source_settings(self, test_auth_source, live_client: VergeClient) -> None:
        """Test updating auth source settings."""
        updated = live_client.auth_sources.update(
            test_auth_source.key,
            settings={
                "server_url": "https://new-example.com/.well-known/openid-configuration",
                "client_id": "updated-client-id",
                "client_secret": "updated-secret",
            },
        )

        # Retrieve with settings to verify
        retrieved = live_client.auth_sources.get(updated.key, include_settings=True)
        assert retrieved.settings.get("client_id") == "updated-client-id"

    def test_delete_auth_source(self, live_client: VergeClient) -> None:
        """Test deleting an auth source."""
        source = live_client.auth_sources.create(
            name="pytest_delete_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
        )

        # Delete
        live_client.auth_sources.delete(source.key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.auth_sources.get(source.key)

    def test_delete_via_object_method(self, live_client: VergeClient) -> None:
        """Test deleting via AuthSource.delete() method."""
        source = live_client.auth_sources.create(
            name="pytest_obj_delete_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
        )

        # Delete via method
        source.delete()

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.auth_sources.get(source.key)


@pytest.mark.integration
class TestAuthSourceProperties:
    """Integration tests for auth source property access."""

    @pytest.fixture
    def test_auth_source(self, live_client: VergeClient):
        """Create a test auth source and cleanup afterwards."""
        source = live_client.auth_sources.create(
            name="pytest_props_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "prop-test-client",
                "client_secret": "prop-test-secret",
            },
            menu=True,
            button_background_color="#333333",
            button_color="#ffffff",
            button_fa_icon="bi-key",
        )
        yield source
        with contextlib.suppress(NotFoundError):
            live_client.auth_sources.delete(source.key)

    def test_auth_source_basic_properties(self, test_auth_source, live_client: VergeClient) -> None:
        """Test accessing basic properties on auth source."""
        source = live_client.auth_sources.get(test_auth_source.key)

        assert isinstance(source, AuthSource)
        assert source.key == test_auth_source.key
        assert source.name == "pytest_props_test"
        assert source.driver == "openid-well-known"

    def test_auth_source_driver_properties(
        self, test_auth_source, live_client: VergeClient
    ) -> None:
        """Test driver type checking properties."""
        source = live_client.auth_sources.get(test_auth_source.key)

        assert source.is_openid is True
        assert source.is_azure is False
        assert source.is_google is False
        assert source.is_gitlab is False
        assert source.is_okta is False
        assert source.is_oauth2 is False
        assert source.is_vergeos is False

    def test_auth_source_menu_property(self, test_auth_source, live_client: VergeClient) -> None:
        """Test menu property."""
        source = live_client.auth_sources.get(test_auth_source.key)
        assert source.is_menu is True

    def test_auth_source_button_style(self, test_auth_source, live_client: VergeClient) -> None:
        """Test button style properties."""
        source = live_client.auth_sources.get(test_auth_source.key)
        style = source.button_style

        assert isinstance(style, dict)
        assert style["background_color"] == "#333333"
        assert style["text_color"] == "#ffffff"
        assert style["icon"] == "bi-key"


@pytest.mark.integration
class TestAuthSourceDebugMode:
    """Integration tests for auth source debug mode."""

    @pytest.fixture
    def test_auth_source(self, live_client: VergeClient):
        """Create a test auth source and cleanup afterwards."""
        source = live_client.auth_sources.create(
            name="pytest_debug_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "debug-test-client",
                "client_secret": "debug-test-secret",
            },
        )
        yield source
        with contextlib.suppress(NotFoundError):
            live_client.auth_sources.delete(source.key)

    def test_enable_debug_mode(self, test_auth_source, live_client: VergeClient) -> None:
        """Test enabling debug mode."""
        # Verify initially not in debug mode
        source = live_client.auth_sources.get(test_auth_source.key)
        assert source.is_debug_enabled is False

        # Enable debug mode
        updated = source.enable_debug()
        assert updated.is_debug_enabled is True

        # Verify persisted
        retrieved = live_client.auth_sources.get(test_auth_source.key)
        assert retrieved.is_debug_enabled is True

    def test_disable_debug_mode(self, test_auth_source, live_client: VergeClient) -> None:
        """Test disabling debug mode."""
        # Enable first
        source = live_client.auth_sources.get(test_auth_source.key)
        source.enable_debug()

        # Disable
        updated = source.disable_debug()
        assert updated.is_debug_enabled is False

        # Verify persisted
        retrieved = live_client.auth_sources.get(test_auth_source.key)
        assert retrieved.is_debug_enabled is False

    def test_update_debug_via_manager(self, test_auth_source, live_client: VergeClient) -> None:
        """Test updating debug mode via manager."""
        # Enable via manager update
        updated = live_client.auth_sources.update(test_auth_source.key, debug=True)
        assert updated.is_debug_enabled is True

        # Disable via manager update
        updated = live_client.auth_sources.update(test_auth_source.key, debug=False)
        assert updated.is_debug_enabled is False


@pytest.mark.integration
class TestAuthSourceStates:
    """Integration tests for auth source state operations."""

    def test_list_states_empty(self, live_client: VergeClient) -> None:
        """Test listing states (usually empty since they're ephemeral)."""
        states = live_client.auth_source_states.list()
        assert isinstance(states, list)

    def test_list_states_for_auth_source(self, live_client: VergeClient) -> None:
        """Test listing states for a specific auth source."""
        # Create a test auth source
        source = live_client.auth_sources.create(
            name="pytest_state_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "state-test-client",
                "client_secret": "state-test-secret",
            },
        )

        try:
            # List states for this source (likely empty)
            states = live_client.auth_source_states.list(auth_source=source.key)
            assert isinstance(states, list)

            # Also test via source object
            scoped_states = source.states.list()
            assert isinstance(scoped_states, list)
        finally:
            with contextlib.suppress(NotFoundError):
                live_client.auth_sources.delete(source.key)

    def test_states_scoped_manager(self, live_client: VergeClient) -> None:
        """Test getting scoped state manager from auth source."""
        # Create a test auth source
        source = live_client.auth_sources.create(
            name="pytest_scoped_state_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "scoped-test-client",
                "client_secret": "scoped-test-secret",
            },
        )

        try:
            # Get scoped manager via manager method
            scoped_mgr = live_client.auth_sources.states(source.key)
            states = scoped_mgr.list()
            assert isinstance(states, list)
        finally:
            with contextlib.suppress(NotFoundError):
                live_client.auth_sources.delete(source.key)


@pytest.mark.integration
class TestAuthSourceRefresh:
    """Integration tests for auth source refresh functionality."""

    @pytest.fixture
    def test_auth_source(self, live_client: VergeClient):
        """Create a test auth source and cleanup afterwards."""
        source = live_client.auth_sources.create(
            name="pytest_refresh_test",
            driver="openid-well-known",
            settings={
                "server_url": "https://example.com/.well-known/openid-configuration",
                "client_id": "refresh-test-client",
                "client_secret": "refresh-test-secret",
            },
        )
        yield source
        with contextlib.suppress(NotFoundError):
            live_client.auth_sources.delete(source.key)

    def test_refresh_auth_source(self, test_auth_source, live_client: VergeClient) -> None:
        """Test refreshing an auth source."""
        # Update via manager
        live_client.auth_sources.update(test_auth_source.key, name="pytest_refreshed_name")

        # Original object still has old name
        assert test_auth_source.name == "pytest_refresh_test"

        # Refresh to get new data
        refreshed = test_auth_source.refresh()
        assert refreshed.name == "pytest_refreshed_name"

    def test_save_auth_source(self, test_auth_source, live_client: VergeClient) -> None:
        """Test saving changes via object method."""
        updated = test_auth_source.save(name="pytest_saved_name")
        assert updated.name == "pytest_saved_name"

        # Verify persisted
        retrieved = live_client.auth_sources.get(test_auth_source.key)
        assert retrieved.name == "pytest_saved_name"
