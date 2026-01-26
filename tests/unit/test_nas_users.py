"""Unit tests for NAS local user operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.nas_users import NASUser, NASUserManager


class TestNASUser:
    """Tests for NASUser resource object."""

    def test_key_property(self) -> None:
        """Test key property returns string."""
        data = {"$key": "abc123def456"}
        user = NASUser(data, MagicMock())
        assert user.key == "abc123def456"

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        user = NASUser({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = user.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": "abc", "name": "testuser"}
        user = NASUser(data, MagicMock())
        assert user.name == "testuser"

    def test_displayname_property(self) -> None:
        """Test displayname property."""
        data = {"$key": "abc", "displayname": "Test User"}
        user = NASUser(data, MagicMock())
        assert user.displayname == "Test User"

    def test_service_key_property(self) -> None:
        """Test service_key property."""
        data = {"$key": "abc", "service": 1}
        user = NASUser(data, MagicMock())
        assert user.service_key == 1

    def test_service_key_property_none(self) -> None:
        """Test service_key property when not set."""
        user = NASUser({"$key": "abc"}, MagicMock())
        assert user.service_key is None

    def test_service_name_property(self) -> None:
        """Test service_name property."""
        data = {"$key": "abc", "service_name": "NAS01"}
        user = NASUser(data, MagicMock())
        assert user.service_name == "NAS01"

    def test_service_name_from_display(self) -> None:
        """Test service_name falls back to service_display."""
        data = {"$key": "abc", "service_display": "NAS01"}
        user = NASUser(data, MagicMock())
        assert user.service_name == "NAS01"

    def test_home_share_key_property(self) -> None:
        """Test home_share_key property."""
        data = {"$key": "abc", "home_share": 5}
        user = NASUser(data, MagicMock())
        assert user.home_share_key == 5

    def test_home_share_name_property(self) -> None:
        """Test home_share_name property."""
        data = {"$key": "abc", "home_share_display": "UserHome"}
        user = NASUser(data, MagicMock())
        assert user.home_share_name == "UserHome"

    def test_home_drive_property(self) -> None:
        """Test home_drive property."""
        data = {"$key": "abc", "home_drive": "H"}
        user = NASUser(data, MagicMock())
        assert user.home_drive == "H"

    def test_is_enabled_true(self) -> None:
        """Test is_enabled property when enabled."""
        data = {"$key": "abc", "enabled": True}
        user = NASUser(data, MagicMock())
        assert user.is_enabled is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled property when disabled."""
        data = {"$key": "abc", "enabled": False}
        user = NASUser(data, MagicMock())
        assert user.is_enabled is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled property defaults to False."""
        user = NASUser({"$key": "abc"}, MagicMock())
        assert user.is_enabled is False

    def test_status_property(self) -> None:
        """Test status property."""
        data = {"$key": "abc", "status_value": "online"}
        user = NASUser(data, MagicMock())
        assert user.status == "online"

    def test_status_fallback(self) -> None:
        """Test status property falls back to 'status'."""
        data = {"$key": "abc", "status": "offline"}
        user = NASUser(data, MagicMock())
        assert user.status == "offline"

    def test_status_display_enabled(self) -> None:
        """Test status_display for enabled user."""
        data = {"$key": "abc", "status_value": "online"}
        user = NASUser(data, MagicMock())
        assert user.status_display == "Enabled"

    def test_status_display_disabled(self) -> None:
        """Test status_display for disabled user."""
        data = {"$key": "abc", "status_value": "offline"}
        user = NASUser(data, MagicMock())
        assert user.status_display == "Disabled"

    def test_status_display_error(self) -> None:
        """Test status_display for error state."""
        data = {"$key": "abc", "status_value": "error"}
        user = NASUser(data, MagicMock())
        assert user.status_display == "Error"

    def test_status_display_unknown(self) -> None:
        """Test status_display for unknown state."""
        data = {"$key": "abc", "status_value": "pending"}
        user = NASUser(data, MagicMock())
        assert user.status_display == "pending"

    def test_status_display_none(self) -> None:
        """Test status_display when status is None."""
        user = NASUser({"$key": "abc"}, MagicMock())
        assert user.status_display == "Unknown"

    def test_user_sid_property(self) -> None:
        """Test user_sid property."""
        data = {"$key": "abc", "user_sid": "S-1-5-21-123"}
        user = NASUser(data, MagicMock())
        assert user.user_sid == "S-1-5-21-123"

    def test_group_sid_property(self) -> None:
        """Test group_sid property."""
        data = {"$key": "abc", "group_sid": "S-1-5-21-456"}
        user = NASUser(data, MagicMock())
        assert user.group_sid == "S-1-5-21-456"

    def test_user_id_property(self) -> None:
        """Test user_id property (Unix UID)."""
        data = {"$key": "abc", "user_id": 1000}
        user = NASUser(data, MagicMock())
        assert user.user_id == 1000

    def test_group_id_property(self) -> None:
        """Test group_id property (Unix GID)."""
        data = {"$key": "abc", "group_id": 1000}
        user = NASUser(data, MagicMock())
        assert user.group_id == 1000

    def test_refresh(self) -> None:
        """Test refresh method calls manager.get."""
        manager = MagicMock(spec=NASUserManager)
        refreshed = NASUser({"$key": "xyz", "name": "refreshed"}, manager)
        manager.get.return_value = refreshed

        user = NASUser({"$key": "abc123"}, manager)
        result = user.refresh()

        manager.get.assert_called_once_with("abc123")
        assert result.name == "refreshed"

    def test_save(self) -> None:
        """Test save method calls manager.update."""
        manager = MagicMock(spec=NASUserManager)
        updated = NASUser({"$key": "abc", "displayname": "Updated"}, manager)
        manager.update.return_value = updated

        user = NASUser({"$key": "abc123"}, manager)
        result = user.save(displayname="Updated")

        manager.update.assert_called_once_with("abc123", displayname="Updated")
        assert result.displayname == "Updated"

    def test_delete(self) -> None:
        """Test delete method calls manager.delete."""
        manager = MagicMock(spec=NASUserManager)

        user = NASUser({"$key": "abc123"}, manager)
        user.delete()

        manager.delete.assert_called_once_with("abc123")


class TestNASUserManager:
    """Tests for NASUserManager operations."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> NASUserManager:
        """Create a NASUserManager with mock client."""
        return NASUserManager(mock_client)

    def test_list_all(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing all users."""
        mock_client._request.return_value = [
            {"$key": "abc1", "name": "user1", "enabled": True},
            {"$key": "abc2", "name": "user2", "enabled": False},
        ]

        users = manager.list(service=1)

        assert len(users) == 2
        assert users[0].name == "user1"
        assert users[1].name == "user2"
        mock_client._request.assert_called_once()

    def test_list_with_service_filter(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test listing users with service filter."""
        mock_client._request.return_value = [{"$key": "abc", "name": "user1"}]

        manager.list(service=1)

        call_args = mock_client._request.call_args
        assert "service eq 1" in call_args[1]["params"]["filter"]

    def test_list_with_enabled_filter(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test listing users with enabled filter."""
        mock_client._request.return_value = []

        manager.list(service=1, enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_with_disabled_filter(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test listing users with disabled filter."""
        mock_client._request.return_value = []

        manager.list(service=1, enabled=False)

        call_args = mock_client._request.call_args
        assert "enabled eq false" in call_args[1]["params"]["filter"]

    def test_list_empty(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing returns empty list when none found."""
        mock_client._request.return_value = None

        users = manager.list(service=1)

        assert users == []

    def test_list_single_result(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with single result (not array)."""
        mock_client._request.return_value = {"$key": "abc", "name": "user1"}

        users = manager.list(service=1)

        assert len(users) == 1
        assert users[0].name == "user1"

    def test_list_with_service_name(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with service name resolution."""
        # First call resolves service name, second lists users
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            [{"$key": "abc", "name": "user1"}],  # User list
        ]

        users = manager.list(service="NAS01")

        assert len(users) == 1
        assert mock_client._request.call_count == 2

    def test_get_by_key(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test getting user by key."""
        mock_client._request.return_value = [
            {"$key": "abc123", "name": "testuser", "enabled": True}
        ]

        user = manager.get("abc123")

        assert user.key == "abc123"
        assert user.name == "testuser"
        call_args = mock_client._request.call_args
        assert "$key eq 'abc123'" in call_args[1]["params"]["filter"]

    def test_get_by_key_not_found(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test getting user by key when not found."""
        mock_client._request.return_value = []

        from pyvergeos.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="not found"):
            manager.get("nonexistent")

    def test_get_by_key_none_response(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test getting user by key with None response."""
        mock_client._request.return_value = None

        from pyvergeos.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            manager.get("abc123")

    def test_get_by_name(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test getting user by name."""
        # When service is an int, no service lookup needed
        mock_client._request.return_value = [{"$key": "abc123", "name": "testuser"}]

        user = manager.get(name="testuser", service=1)

        assert user.name == "testuser"

    def test_get_by_name_without_service(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test getting user by name without service raises."""
        with pytest.raises(ValueError, match="service is required"):
            manager.get(name="testuser")

    def test_get_by_name_not_found(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test getting user by name when not found."""
        # When service is an int, no service lookup needed - just empty user list
        mock_client._request.return_value = []

        from pyvergeos.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="not found"):
            manager.get(name="nonexistent", service=1)

    def test_get_no_identifier(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test getting user without key or name raises."""
        with pytest.raises(ValueError, match="key or name"):
            manager.get()

    def test_create_basic(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test creating a basic user."""
        mock_client._request.side_effect = [
            {"$key": "newkey123"},  # Create response
            [{"$key": "newkey123", "name": "newuser", "enabled": True}],  # Get
        ]

        user = manager.create(service=1, name="newuser", password="TestPass123!")

        assert user.name == "newuser"
        # Check create request
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0] == ("POST", "vm_service_users")
        body = create_call[1]["json_data"]
        assert body["service"] == 1
        assert body["name"] == "newuser"
        assert body["password"] == "TestPass123!"
        assert body["enabled"] is True

    def test_create_with_all_options(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test creating user with all options."""
        mock_client._request.side_effect = [
            [{"$key": 5}],  # CIFS share lookup
            {"$key": "newkey"},  # Create response
            [{"$key": "newkey", "name": "admin"}],  # Get
        ]

        user = manager.create(
            service=1,
            name="admin",
            password="AdminPass!",
            displayname="Administrator",
            description="Admin account",
            home_share="AdminDocs",
            home_drive="H",
            enabled=True,
        )

        assert user.name == "admin"
        # Check the create body
        create_call = mock_client._request.call_args_list[1]
        body = create_call[1]["json_data"]
        assert body["displayname"] == "Administrator"
        assert body["description"] == "Admin account"
        assert body["home_share"] == 5
        assert body["home_drive"] == "H"

    def test_create_with_service_name(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test creating user with service name resolution."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            {"$key": "newkey"},  # Create
            [{"$key": "newkey", "name": "user"}],  # Get
        ]

        user = manager.create(service="NAS01", name="user", password="pass")

        assert user.name == "user"
        # Check service was resolved
        assert mock_client._request.call_count == 3

    def test_create_service_not_found(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test creating user with invalid service."""
        mock_client._request.return_value = []  # Service not found

        with pytest.raises(ValueError, match="not found"):
            manager.create(service="InvalidNAS", name="user", password="pass")

    def test_create_disabled(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test creating disabled user."""
        mock_client._request.side_effect = [
            {"$key": "newkey"},  # Create
            [{"$key": "newkey", "name": "user", "enabled": False}],  # Get
        ]

        manager.create(service=1, name="user", password="pass", enabled=False)

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["enabled"] is False

    def test_update_password(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test updating user password."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "name": "user"}],  # GET
        ]

        manager.update("abc123", password="NewPass!")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "vm_service_users/abc123")
        assert put_call[1]["json_data"]["password"] == "NewPass!"

    def test_update_displayname(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test updating display name."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "displayname": "New Name"}],  # GET
        ]

        user = manager.update("abc123", displayname="New Name")

        assert user.displayname == "New Name"
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["displayname"] == "New Name"

    def test_update_enabled(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test updating enabled state."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "enabled": False}],  # GET
        ]

        manager.update("abc123", enabled=False)

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False

    def test_update_home_drive(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test updating home drive (uppercase)."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "home_drive": "Z"}],  # GET
        ]

        manager.update("abc123", home_drive="z")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["home_drive"] == "Z"

    def test_update_clear_home_drive(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test clearing home drive."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123"}],  # GET
        ]

        manager.update("abc123", home_drive="")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["home_drive"] == ""

    def test_update_no_changes(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test update with no changes just fetches."""
        mock_client._request.return_value = [{"$key": "abc123", "name": "user"}]

        manager.update("abc123")

        # Only one call (GET), no PUT
        assert mock_client._request.call_count == 1
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"

    def test_delete(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test deleting user."""
        mock_client._request.return_value = None

        manager.delete("abc123")

        mock_client._request.assert_called_once_with("DELETE", "vm_service_users/abc123")

    def test_enable(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test enabling user."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "enabled": True}],  # GET
        ]

        user = manager.enable("abc123")

        assert user.is_enabled is True
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is True

    def test_disable(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test disabling user."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "abc123", "enabled": False}],  # GET
        ]

        user = manager.disable("abc123")

        assert user.is_enabled is False
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["enabled"] is False

    def test_resolve_service_key_int(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test service key resolution with integer."""
        result = manager._resolve_service_key(42)
        assert result == 42

    def test_resolve_service_key_string(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test service key resolution with name."""
        mock_client._request.return_value = [{"$key": 1, "name": "NAS01"}]

        result = manager._resolve_service_key("NAS01")

        assert result == 1
        call_args = mock_client._request.call_args
        # Should query vm_services endpoint, not vms
        assert call_args[0][1] == "vm_services"
        assert "NAS01" in call_args[1]["params"]["filter"]

    def test_resolve_service_key_not_found(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test service key resolution when not found."""
        mock_client._request.return_value = []

        result = manager._resolve_service_key("NonExistent")

        assert result is None

    def test_resolve_cifs_share_key_int(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test CIFS share key resolution with integer."""
        result = manager._resolve_cifs_share_key(42, 1)
        assert result == 42

    def test_resolve_cifs_share_key_string(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test CIFS share key resolution with name."""
        mock_client._request.return_value = [{"$key": 5, "name": "UserHome"}]

        result = manager._resolve_cifs_share_key("UserHome", 1)

        assert result == 5
        call_args = mock_client._request.call_args
        assert "UserHome" in call_args[1]["params"]["filter"]
        assert "volume#service eq 1" in call_args[1]["params"]["filter"]

    def test_to_model(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test _to_model creates proper NASUser object."""
        data = {
            "$key": "abc123",
            "name": "testuser",
            "enabled": True,
            "service": 1,
        }

        user = manager._to_model(data)

        assert isinstance(user, NASUser)
        assert user.key == "abc123"
        assert user.name == "testuser"
        assert user.is_enabled is True


class TestNASUserManagerPagination:
    """Tests for pagination in NASUserManager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> NASUserManager:
        """Create a NASUserManager with mock client."""
        return NASUserManager(mock_client)

    def test_list_with_limit(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with limit."""
        mock_client._request.return_value = [{"$key": "abc", "name": "user1"}]

        manager.list(service=1, limit=10)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10

    def test_list_with_offset(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with offset."""
        mock_client._request.return_value = []

        manager.list(service=1, offset=20)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["offset"] == 20

    def test_list_with_limit_and_offset(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test listing with both limit and offset."""
        mock_client._request.return_value = []

        manager.list(service=1, limit=10, offset=20)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["offset"] == 20


class TestNASUserManagerFilters:
    """Tests for filter handling in NASUserManager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> NASUserManager:
        """Create a NASUserManager with mock client."""
        return NASUserManager(mock_client)

    def test_list_with_custom_filter(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with custom OData filter."""
        mock_client._request.return_value = []

        manager.list(filter="name ct 'admin'")

        call_args = mock_client._request.call_args
        assert "name ct 'admin'" in call_args[1]["params"]["filter"]

    def test_list_with_name_filter_kwargs(
        self, manager: NASUserManager, mock_client: MagicMock
    ) -> None:
        """Test listing with name filter via kwargs."""
        mock_client._request.return_value = []

        manager.list(service=1, name="testuser")

        call_args = mock_client._request.call_args
        assert "name eq 'testuser'" in call_args[1]["params"]["filter"]

    def test_list_combines_filters(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test that multiple filters are combined with 'and'."""
        mock_client._request.return_value = []

        manager.list(
            filter="custom eq 'value'",
            service=1,
            enabled=True,
        )

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "custom eq 'value'" in filter_str
        assert "service eq 1" in filter_str
        assert "enabled eq true" in filter_str
        assert " and " in filter_str

    def test_list_with_custom_fields(self, manager: NASUserManager, mock_client: MagicMock) -> None:
        """Test listing with custom fields."""
        mock_client._request.return_value = [{"$key": "abc", "name": "user"}]

        manager.list(service=1, fields=["$key", "name"])

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["fields"] == "$key,name"
