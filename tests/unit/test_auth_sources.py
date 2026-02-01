"""Unit tests for authentication source resources."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.client import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.auth_sources import (
    AuthSource,
    AuthSourceManager,
    AuthSourceState,
    AuthSourceStateManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client.is_connected = True
    return client


# =============================================================================
# AuthSourceStateManager Tests
# =============================================================================


class TestAuthSourceStateManager:
    """Tests for AuthSourceStateManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = AuthSourceStateManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "auth_source_states"
        assert manager._auth_source_key is None

    def test_init_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager initialization."""
        manager = AuthSourceStateManager(mock_client, auth_source_key=1)
        assert manager._auth_source_key == 1

    def test_list_returns_states(self, mock_client: MagicMock) -> None:
        """Test listing states."""
        mock_client._request.return_value = [
            {"$key": "a" * 40, "state": "a" * 40, "auth_source": 1},
            {"$key": "b" * 40, "state": "b" * 40, "auth_source": 1},
        ]

        manager = AuthSourceStateManager(mock_client)
        states = manager.list()

        assert len(states) == 2
        assert isinstance(states[0], AuthSourceState)

    def test_list_with_auth_source_filter(self, mock_client: MagicMock) -> None:
        """Test listing with auth_source filter."""
        mock_client._request.return_value = []

        manager = AuthSourceStateManager(mock_client)
        manager.list(auth_source=1)

        call_args = mock_client._request.call_args
        assert "auth_source eq 1" in call_args[1]["params"]["filter"]

    def test_list_scoped_filters_by_auth_source(self, mock_client: MagicMock) -> None:
        """Test scoped manager auto-filters by auth source."""
        mock_client._request.return_value = []

        manager = AuthSourceStateManager(mock_client, auth_source_key=5)
        manager.list()

        call_args = mock_client._request.call_args
        assert "auth_source eq 5" in call_args[1]["params"]["filter"]

    def test_list_returns_empty_on_none(self, mock_client: MagicMock) -> None:
        """Test listing returns empty list on None response."""
        mock_client._request.return_value = None

        manager = AuthSourceStateManager(mock_client)
        states = manager.list()

        assert states == []

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting state by key."""
        state_key = "a" * 40
        mock_client._request.return_value = [
            {"$key": state_key, "state": state_key, "auth_source": 1},
        ]

        manager = AuthSourceStateManager(mock_client)
        state = manager.get(key=state_key)

        assert isinstance(state, AuthSourceState)
        assert state.key == state_key

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = []

        manager = AuthSourceStateManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key="nonexistent" + "0" * 30)

    def test_get_requires_key(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without key."""
        manager = AuthSourceStateManager(mock_client)
        with pytest.raises(ValueError, match="Key must be provided"):
            manager.get()


class TestAuthSourceState:
    """Tests for AuthSourceState resource object."""

    def test_key_property(self, mock_client: MagicMock) -> None:
        """Test key property returns state."""
        state_key = "a" * 40
        manager = AuthSourceStateManager(mock_client)
        state = AuthSourceState({"state": state_key}, manager)

        assert state.key == state_key

    def test_key_from_key_field(self, mock_client: MagicMock) -> None:
        """Test key property falls back to $key."""
        state_key = "a" * 40
        manager = AuthSourceStateManager(mock_client)
        state = AuthSourceState({"$key": state_key}, manager)

        assert state.key == state_key

    def test_key_raises_without_key(self, mock_client: MagicMock) -> None:
        """Test key raises ValueError when not set."""
        manager = AuthSourceStateManager(mock_client)
        state = AuthSourceState({}, manager)

        with pytest.raises(ValueError, match="State has no key"):
            _ = state.key

    def test_auth_source_key_property(self, mock_client: MagicMock) -> None:
        """Test auth_source_key property."""
        manager = AuthSourceStateManager(mock_client)
        state = AuthSourceState({"auth_source": 5}, manager)

        assert state.auth_source_key == 5

    def test_is_expired_fresh(self, mock_client: MagicMock) -> None:
        """Test is_expired returns False for fresh state."""
        import time

        manager = AuthSourceStateManager(mock_client)
        # Timestamp in microseconds, now - 1 minute
        ts = int((time.time() - 60) * 1_000_000)
        state = AuthSourceState({"timestamp": ts}, manager)

        assert state.is_expired is False

    def test_is_expired_old(self, mock_client: MagicMock) -> None:
        """Test is_expired returns True for old state."""
        import time

        manager = AuthSourceStateManager(mock_client)
        # Timestamp in microseconds, now - 20 minutes (>15 min = expired)
        ts = int((time.time() - 1200) * 1_000_000)
        state = AuthSourceState({"timestamp": ts}, manager)

        assert state.is_expired is True

    def test_is_expired_no_timestamp(self, mock_client: MagicMock) -> None:
        """Test is_expired returns True when no timestamp."""
        manager = AuthSourceStateManager(mock_client)
        state = AuthSourceState({}, manager)

        assert state.is_expired is True


# =============================================================================
# AuthSourceManager Tests
# =============================================================================


class TestAuthSourceManager:
    """Tests for AuthSourceManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = AuthSourceManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "auth_sources"

    def test_list_returns_sources(self, mock_client: MagicMock) -> None:
        """Test listing auth sources."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Azure AD", "driver": "azure"},
            {"$key": 2, "name": "Google", "driver": "google"},
        ]

        manager = AuthSourceManager(mock_client)
        sources = manager.list()

        assert len(sources) == 2
        assert isinstance(sources[0], AuthSource)
        assert sources[0]["name"] == "Azure AD"
        assert sources[1]["driver"] == "google"

    def test_list_with_driver_filter(self, mock_client: MagicMock) -> None:
        """Test listing with driver filter."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Azure AD", "driver": "azure"},
        ]

        manager = AuthSourceManager(mock_client)
        manager.list(driver="azure")

        call_args = mock_client._request.call_args
        assert "driver eq 'azure'" in call_args[1]["params"]["filter"]

    def test_list_returns_empty_on_none(self, mock_client: MagicMock) -> None:
        """Test listing returns empty list on None response."""
        mock_client._request.return_value = None

        manager = AuthSourceManager(mock_client)
        sources = manager.list()

        assert sources == []

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting auth source by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Azure AD",
            "driver": "azure",
        }

        manager = AuthSourceManager(mock_client)
        source = manager.get(key=1)

        assert isinstance(source, AuthSource)
        assert source.key == 1
        assert source["name"] == "Azure AD"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting auth source by name."""
        mock_client._request.return_value = [
            {"$key": 2, "name": "Google", "driver": "google"},
        ]

        manager = AuthSourceManager(mock_client)
        source = manager.get(name="Google")

        assert source["name"] == "Google"

    def test_get_with_include_settings(self, mock_client: MagicMock) -> None:
        """Test get with include_settings includes settings field."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Azure",
            "settings": {"tenant_id": "abc"},
        }

        manager = AuthSourceManager(mock_client)
        manager.get(key=1, include_settings=True)

        call_args = mock_client._request.call_args
        assert "settings" in call_args[1]["params"]["fields"]

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = AuthSourceManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_requires_identifier(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without identifier."""
        manager = AuthSourceManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_create_auth_source(self, mock_client: MagicMock) -> None:
        """Test creating an auth source."""
        mock_client._request.side_effect = [
            {"$key": 3},  # POST response
            {"$key": 3, "name": "Test", "driver": "google"},  # GET response
        ]

        manager = AuthSourceManager(mock_client)
        source = manager.create(
            name="Test",
            driver="google",
            settings={"client_id": "test-id"},
        )

        assert source.key == 3
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "auth_sources")
        body = post_call[1]["json_data"]
        assert body["name"] == "Test"
        assert body["driver"] == "google"
        assert body["settings"]["client_id"] == "test-id"

    def test_create_with_styling(self, mock_client: MagicMock) -> None:
        """Test creating with button styling."""
        mock_client._request.side_effect = [
            {"$key": 3},
            {"$key": 3, "name": "Google", "driver": "google"},
        ]

        manager = AuthSourceManager(mock_client)
        manager.create(
            name="Google",
            driver="google",
            button_background_color="#4285F4",
            button_color="#ffffff",
            button_fa_icon="bi-google",
            icon_color="#ffffff",
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["button_background_color"] == "#4285F4"
        assert body["button_color"] == "#ffffff"
        assert body["button_fa_icon"] == "bi-google"
        assert body["icon_color"] == "#ffffff"

    def test_update_auth_source(self, mock_client: MagicMock) -> None:
        """Test updating an auth source."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated", "driver": "google"},  # GET response
        ]

        manager = AuthSourceManager(mock_client)
        manager.update(key=1, name="Updated", debug=True)

        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "auth_sources/1")
        body = put_call[1]["json_data"]
        assert body["name"] == "Updated"
        assert body["debug"] is True

    def test_update_no_changes(self, mock_client: MagicMock) -> None:
        """Test update with no changes returns current source."""
        mock_client._request.return_value = {"$key": 1, "name": "Test"}

        manager = AuthSourceManager(mock_client)
        manager.update(key=1)

        mock_client._request.assert_called_once()
        assert mock_client._request.call_args[0][0] == "GET"

    def test_delete_auth_source(self, mock_client: MagicMock) -> None:
        """Test deleting an auth source."""
        mock_client._request.return_value = None

        manager = AuthSourceManager(mock_client)
        manager.delete(key=1)

        mock_client._request.assert_called_once_with("DELETE", "auth_sources/1")

    def test_states_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test states() returns scoped AuthSourceStateManager."""
        manager = AuthSourceManager(mock_client)
        state_mgr = manager.states(key=5)

        assert isinstance(state_mgr, AuthSourceStateManager)
        assert state_mgr._auth_source_key == 5


class TestAuthSource:
    """Tests for AuthSource resource object."""

    def test_driver_property(self, mock_client: MagicMock) -> None:
        """Test driver property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "azure"}, manager)

        assert source.driver == "azure"

    def test_is_azure(self, mock_client: MagicMock) -> None:
        """Test is_azure property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "azure"}, manager)

        assert source.is_azure is True
        assert source.is_google is False

    def test_is_google(self, mock_client: MagicMock) -> None:
        """Test is_google property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "google"}, manager)

        assert source.is_google is True
        assert source.is_azure is False

    def test_is_gitlab(self, mock_client: MagicMock) -> None:
        """Test is_gitlab property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "gitlab"}, manager)

        assert source.is_gitlab is True

    def test_is_okta(self, mock_client: MagicMock) -> None:
        """Test is_okta property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "okta"}, manager)

        assert source.is_okta is True

    def test_is_openid(self, mock_client: MagicMock) -> None:
        """Test is_openid property."""
        manager = AuthSourceManager(mock_client)

        source1 = AuthSource({"driver": "openid"}, manager)
        assert source1.is_openid is True

        source2 = AuthSource({"driver": "openid-well-known"}, manager)
        assert source2.is_openid is True

    def test_is_oauth2(self, mock_client: MagicMock) -> None:
        """Test is_oauth2 property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "oauth2"}, manager)

        assert source.is_oauth2 is True

    def test_is_vergeos(self, mock_client: MagicMock) -> None:
        """Test is_vergeos property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"driver": "verge.io"}, manager)

        assert source.is_vergeos is True

    def test_settings_property(self, mock_client: MagicMock) -> None:
        """Test settings property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource(
            {"settings": {"client_id": "abc", "tenant_id": "xyz"}},
            manager,
        )

        assert source.settings == {"client_id": "abc", "tenant_id": "xyz"}

    def test_settings_empty(self, mock_client: MagicMock) -> None:
        """Test settings returns empty dict when not set."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({}, manager)

        assert source.settings == {}

    def test_is_debug_enabled(self, mock_client: MagicMock) -> None:
        """Test is_debug_enabled property."""
        manager = AuthSourceManager(mock_client)

        source1 = AuthSource({"debug": True}, manager)
        assert source1.is_debug_enabled is True

        source2 = AuthSource({"debug": False}, manager)
        assert source2.is_debug_enabled is False

    def test_is_menu(self, mock_client: MagicMock) -> None:
        """Test is_menu property."""
        manager = AuthSourceManager(mock_client)

        source1 = AuthSource({"menu": True}, manager)
        assert source1.is_menu is True

        source2 = AuthSource({"menu": False}, manager)
        assert source2.is_menu is False

    def test_button_style(self, mock_client: MagicMock) -> None:
        """Test button_style property."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource(
            {
                "button_background_color": "#4285F4",
                "button_color": "#fff",
                "button_fa_icon": "bi-google",
                "icon_color": "#fff",
            },
            manager,
        )

        style = source.button_style
        assert style["background_color"] == "#4285F4"
        assert style["text_color"] == "#fff"
        assert style["icon"] == "bi-google"
        assert style["icon_color"] == "#fff"

    def test_states_property(self, mock_client: MagicMock) -> None:
        """Test states property returns scoped manager."""
        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 5}, manager)

        state_mgr = source.states
        assert isinstance(state_mgr, AuthSourceStateManager)
        assert state_mgr._auth_source_key == 5

    def test_enable_debug(self, mock_client: MagicMock) -> None:
        """Test enable_debug calls update."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "debug": True},  # GET
        ]

        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 1}, manager)
        result = source.enable_debug()

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["debug"] is True
        assert result["debug"] is True

    def test_disable_debug(self, mock_client: MagicMock) -> None:
        """Test disable_debug calls update."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "debug": False},  # GET
        ]

        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 1, "debug": True}, manager)
        result = source.disable_debug()

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["debug"] is False
        assert result["debug"] is False

    def test_refresh(self, mock_client: MagicMock) -> None:
        """Test refresh reloads from API."""
        mock_client._request.return_value = {"$key": 1, "name": "Updated"}

        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 1, "name": "Old"}, manager)
        refreshed = source.refresh()

        assert refreshed["name"] == "Updated"

    def test_save(self, mock_client: MagicMock) -> None:
        """Test save calls update."""
        mock_client._request.side_effect = [
            None,  # PUT
            {"$key": 1, "name": "New Name"},  # GET
        ]

        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 1, "name": "Old"}, manager)
        result = source.save(name="New Name")

        assert result["name"] == "New Name"

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test delete."""
        mock_client._request.return_value = None

        manager = AuthSourceManager(mock_client)
        source = AuthSource({"$key": 1}, manager)
        source.delete()

        mock_client._request.assert_called_once_with("DELETE", "auth_sources/1")
