"""Unit tests for API key operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.api_keys import APIKey, APIKeyCreated, APIKeyManager


class TestAPIKeyCreated:
    """Tests for APIKeyCreated response object."""

    def test_init_and_attributes(self) -> None:
        """Test APIKeyCreated initialization."""
        result = APIKeyCreated(
            key=1,
            name="test-key",
            user_key=10,
            user_name="admin",
            secret="abc123secret",
        )
        assert result.key == 1
        assert result.name == "test-key"
        assert result.user_key == 10
        assert result.user_name == "admin"
        assert result.secret == "abc123secret"

    def test_repr_hides_secret(self) -> None:
        """Test repr does not expose the secret."""
        result = APIKeyCreated(
            key=1,
            name="test-key",
            user_key=10,
            user_name="admin",
            secret="abc123secret",
        )
        repr_str = repr(result)
        assert "abc123secret" not in repr_str
        assert "***" in repr_str
        assert "test-key" in repr_str


class TestAPIKey:
    """Tests for APIKey resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        api_key = APIKey(data, MagicMock())
        assert api_key.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        api_key = APIKey({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = api_key.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "my-api-key"}
        api_key = APIKey(data, MagicMock())
        assert api_key.name == "my-api-key"

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Test description"}
        api_key = APIKey(data, MagicMock())
        assert api_key.description == "Test description"

    def test_description_none(self) -> None:
        """Test description property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.description is None

    def test_user_key_property(self) -> None:
        """Test user_key property."""
        data = {"$key": 1, "user": 10}
        api_key = APIKey(data, MagicMock())
        assert api_key.user_key == 10

    def test_user_key_default(self) -> None:
        """Test user_key property defaults to 0."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.user_key == 0

    def test_user_name_property(self) -> None:
        """Test user_name property."""
        data = {"$key": 1, "user_name": "admin"}
        api_key = APIKey(data, MagicMock())
        assert api_key.user_name == "admin"

    def test_user_name_none(self) -> None:
        """Test user_name property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.user_name is None

    def test_created_property(self) -> None:
        """Test created property."""
        data = {"$key": 1, "created": 1700000000}
        api_key = APIKey(data, MagicMock())
        assert api_key.created == 1700000000

    def test_created_none(self) -> None:
        """Test created property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.created is None

    def test_created_datetime(self) -> None:
        """Test created_datetime property."""
        data = {"$key": 1, "created": 1700000000}
        api_key = APIKey(data, MagicMock())
        dt = api_key.created_datetime
        assert dt is not None
        assert dt.year == 2023
        assert dt.month == 11

    def test_created_datetime_none(self) -> None:
        """Test created_datetime property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.created_datetime is None

    def test_expires_property(self) -> None:
        """Test expires property."""
        data = {"$key": 1, "expires": 1700000000}
        api_key = APIKey(data, MagicMock())
        assert api_key.expires == 1700000000

    def test_expires_zero(self) -> None:
        """Test expires property returns None for zero (never expires)."""
        data = {"$key": 1, "expires": 0}
        api_key = APIKey(data, MagicMock())
        assert api_key.expires is None

    def test_expires_none(self) -> None:
        """Test expires property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.expires is None

    def test_expires_datetime(self) -> None:
        """Test expires_datetime property."""
        data = {"$key": 1, "expires": 1700000000}
        api_key = APIKey(data, MagicMock())
        dt = api_key.expires_datetime
        assert dt is not None
        assert dt.year == 2023

    def test_expires_datetime_none(self) -> None:
        """Test expires_datetime property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.expires_datetime is None

    def test_is_expired_false_never_expires(self) -> None:
        """Test is_expired returns False when no expiration."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.is_expired is False

    def test_is_expired_false_future(self) -> None:
        """Test is_expired returns False when expiration is in future."""
        future = int(datetime.now(tz=timezone.utc).timestamp()) + 86400
        data = {"$key": 1, "expires": future}
        api_key = APIKey(data, MagicMock())
        assert api_key.is_expired is False

    def test_is_expired_true_past(self) -> None:
        """Test is_expired returns True when expiration is in past."""
        past = int(datetime.now(tz=timezone.utc).timestamp()) - 86400
        data = {"$key": 1, "expires": past}
        api_key = APIKey(data, MagicMock())
        assert api_key.is_expired is True

    def test_last_login_property(self) -> None:
        """Test last_login property."""
        data = {"$key": 1, "lastlogin_stamp": 1700000000}
        api_key = APIKey(data, MagicMock())
        assert api_key.last_login == 1700000000

    def test_last_login_zero(self) -> None:
        """Test last_login property returns None for zero (never used)."""
        data = {"$key": 1, "lastlogin_stamp": 0}
        api_key = APIKey(data, MagicMock())
        assert api_key.last_login is None

    def test_last_login_datetime(self) -> None:
        """Test last_login_datetime property."""
        data = {"$key": 1, "lastlogin_stamp": 1700000000}
        api_key = APIKey(data, MagicMock())
        dt = api_key.last_login_datetime
        assert dt is not None
        assert dt.year == 2023

    def test_last_login_datetime_none(self) -> None:
        """Test last_login_datetime property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.last_login_datetime is None

    def test_last_login_ip_property(self) -> None:
        """Test last_login_ip property."""
        data = {"$key": 1, "lastlogin_ip": "192.168.1.100"}
        api_key = APIKey(data, MagicMock())
        assert api_key.last_login_ip == "192.168.1.100"

    def test_last_login_ip_none(self) -> None:
        """Test last_login_ip property when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.last_login_ip is None

    def test_ip_allow_list_property(self) -> None:
        """Test ip_allow_list property parses comma-separated values."""
        data = {"$key": 1, "ip_allow_list": "10.0.0.0/8,192.168.1.100"}
        api_key = APIKey(data, MagicMock())
        assert api_key.ip_allow_list == ["10.0.0.0/8", "192.168.1.100"]

    def test_ip_allow_list_empty(self) -> None:
        """Test ip_allow_list property returns empty list when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.ip_allow_list == []

    def test_ip_allow_list_strips_whitespace(self) -> None:
        """Test ip_allow_list property strips whitespace."""
        data = {"$key": 1, "ip_allow_list": " 10.0.0.0/8 , 192.168.1.100 "}
        api_key = APIKey(data, MagicMock())
        assert api_key.ip_allow_list == ["10.0.0.0/8", "192.168.1.100"]

    def test_ip_deny_list_property(self) -> None:
        """Test ip_deny_list property parses comma-separated values."""
        data = {"$key": 1, "ip_deny_list": "10.0.0.1,10.0.0.2"}
        api_key = APIKey(data, MagicMock())
        assert api_key.ip_deny_list == ["10.0.0.1", "10.0.0.2"]

    def test_ip_deny_list_empty(self) -> None:
        """Test ip_deny_list property returns empty list when not set."""
        api_key = APIKey({"$key": 1}, MagicMock())
        assert api_key.ip_deny_list == []

    def test_delete_method(self) -> None:
        """Test delete method calls manager."""
        manager = MagicMock()
        api_key = APIKey({"$key": 5}, manager)

        api_key.delete()

        manager.delete.assert_called_once_with(5)


class TestAPIKeyManager:
    """Tests for APIKeyManager."""

    def _create_manager(self) -> tuple[APIKeyManager, MagicMock]:
        """Create an APIKeyManager with mocked client."""
        client = MagicMock()
        # Mock users manager for user lookups
        client.users.get.return_value = MagicMock(key=1, name="admin")
        manager = APIKeyManager(client)
        return manager, client

    # list() tests

    def test_list_returns_api_keys(self) -> None:
        """Test list returns APIKey objects."""
        manager, client = self._create_manager()
        client._request.return_value = [
            {"$key": 1, "name": "key1", "user": 10},
            {"$key": 2, "name": "key2", "user": 10},
        ]

        result = manager.list()

        assert len(result) == 2
        assert all(isinstance(k, APIKey) for k in result)
        assert result[0].name == "key1"
        assert result[1].name == "key2"

    def test_list_with_user_key(self) -> None:
        """Test list filters by user key."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(user=10)

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "user eq 10" in filter_param

    def test_list_with_username(self) -> None:
        """Test list filters by username (resolves to key)."""
        manager, client = self._create_manager()
        client._request.return_value = []
        client.users.get.return_value = MagicMock(key=10)

        manager.list(user="admin")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "user eq 10" in filter_param

    def test_list_with_custom_filter(self) -> None:
        """Test list with custom OData filter."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list(filter="name eq 'automation'")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "name eq 'automation'" in filter_param

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

    def test_list_uses_default_fields(self) -> None:
        """Test list uses default fields."""
        manager, client = self._create_manager()
        client._request.return_value = []

        manager.list()

        call_args = client._request.call_args
        fields = call_args.kwargs["params"]["fields"]
        assert "$key" in fields
        assert "user" in fields
        assert "name" in fields
        assert "expires" in fields

    # get() tests

    def test_get_by_key(self) -> None:
        """Test get by key."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "name": "test-key"}

        result = manager.get(1)

        client._request.assert_called_once()
        assert "user_api_keys/1" in client._request.call_args.args[1]
        assert result.name == "test-key"

    def test_get_by_name_and_user(self) -> None:
        """Test get by name with user."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "test-key"}]
        client.users.get.return_value = MagicMock(key=10)

        result = manager.get(name="test-key", user="admin")

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "name eq 'test-key'" in filter_param
        assert "user eq 10" in filter_param
        assert result.name == "test-key"

    def test_get_by_name_escapes_quotes(self) -> None:
        """Test get by name escapes single quotes."""
        manager, client = self._create_manager()
        client._request.return_value = [{"$key": 1, "name": "test'key"}]
        client.users.get.return_value = MagicMock(key=10)

        manager.get(name="test'key", user=10)

        call_args = client._request.call_args
        filter_param = call_args.kwargs["params"]["filter"]
        assert "name eq 'test''key'" in filter_param

    def test_get_not_found_by_key(self) -> None:
        """Test get raises NotFoundError when key not found."""
        manager, client = self._create_manager()
        client._request.return_value = None

        with pytest.raises(NotFoundError, match="key 999"):
            manager.get(999)

    def test_get_not_found_by_name(self) -> None:
        """Test get raises NotFoundError when name not found."""
        manager, client = self._create_manager()
        client._request.return_value = []
        client.users.get.return_value = MagicMock(key=10)

        with pytest.raises(NotFoundError, match="not found"):
            manager.get(name="nonexistent", user=10)

    def test_get_requires_key_or_name(self) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        manager, client = self._create_manager()

        with pytest.raises(ValueError, match="key or name"):
            manager.get()

    def test_get_by_name_requires_user(self) -> None:
        """Test get by name raises ValueError when user not provided."""
        manager, client = self._create_manager()

        with pytest.raises(ValueError, match="user parameter is required"):
            manager.get(name="test-key")

    # create() tests

    def test_create_basic(self) -> None:
        """Test create with required parameters."""
        manager, client = self._create_manager()
        client._request.return_value = {
            "$key": 1,
            "response": {"private_key": "secret123"},
        }
        client.users.get.return_value = MagicMock(key=10, name="admin")

        result = manager.create(user="admin", name="my-key")

        post_call = client._request.call_args
        assert post_call.args[0] == "POST"
        assert post_call.args[1] == "user_api_keys"
        body = post_call.kwargs["json_data"]
        assert body["user"] == 10
        assert body["name"] == "my-key"
        assert body["expires_type"] == "never"

        assert isinstance(result, APIKeyCreated)
        assert result.key == 1
        assert result.name == "my-key"
        assert result.secret == "secret123"

    def test_create_with_user_key(self) -> None:
        """Test create with user key instead of username."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "key": "secret123"}

        manager.create(user=10, name="my-key")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["user"] == 10

    def test_create_with_description(self) -> None:
        """Test create with description."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", description="Test description")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["description"] == "Test description"

    def test_create_with_expires_in_days(self) -> None:
        """Test create with expires_in days format."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", expires_in="30d")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert "expires" in body
        assert body["expires_type"] == "date"
        # Verify expiration is roughly 30 days in future
        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (30 * 86400)
        assert abs(body["expires"] - expected) < 60  # Within 1 minute

    def test_create_with_expires_in_weeks(self) -> None:
        """Test create with expires_in weeks format."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", expires_in="2w")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (14 * 86400)
        assert abs(body["expires"] - expected) < 60

    def test_create_with_expires_in_months(self) -> None:
        """Test create with expires_in months format."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", expires_in="3m")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (90 * 86400)
        assert abs(body["expires"] - expected) < 60

    def test_create_with_expires_in_years(self) -> None:
        """Test create with expires_in years format."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", expires_in="1y")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (365 * 86400)
        assert abs(body["expires"] - expected) < 60

    def test_create_with_expires_in_never(self) -> None:
        """Test create with expires_in='never'."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", expires_in="never")

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["expires_type"] == "never"
        assert "expires" not in body

    def test_create_with_expires_datetime(self) -> None:
        """Test create with specific expiration datetime."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        expires = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        manager.create(user=10, name="my-key", expires=expires)

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["expires"] == int(expires.timestamp())
        assert body["expires_type"] == "date"

    def test_create_with_ip_allow_list(self) -> None:
        """Test create with IP allow list."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", ip_allow_list=["10.0.0.0/8", "192.168.1.100"])

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["ip_allow_list"] == "10.0.0.0/8,192.168.1.100"

    def test_create_with_ip_deny_list(self) -> None:
        """Test create with IP deny list."""
        manager, client = self._create_manager()
        client._request.return_value = {"$key": 1, "response": {"private_key": "secret"}}

        manager.create(user=10, name="my-key", ip_deny_list=["10.0.0.1"])

        post_call = client._request.call_args
        body = post_call.kwargs["json_data"]
        assert body["ip_deny_list"] == "10.0.0.1"

    def test_create_user_not_found(self) -> None:
        """Test create raises NotFoundError when user not found."""
        manager, client = self._create_manager()
        client.users.get.side_effect = NotFoundError("User not found")

        with pytest.raises(NotFoundError, match="not found"):
            manager.create(user="nonexistent", name="my-key")

    # delete() tests

    def test_delete_api_key(self) -> None:
        """Test delete API key."""
        manager, client = self._create_manager()
        client._request.return_value = None

        manager.delete(5)

        client._request.assert_called_once_with("DELETE", "user_api_keys/5")

    # _resolve_user_key() tests

    def test_resolve_user_key_from_int(self) -> None:
        """Test _resolve_user_key returns int directly."""
        manager, client = self._create_manager()

        result = manager._resolve_user_key(10)

        assert result == 10
        client.users.get.assert_not_called()

    def test_resolve_user_key_from_string(self) -> None:
        """Test _resolve_user_key looks up username."""
        manager, client = self._create_manager()
        client.users.get.return_value = MagicMock(key=10)

        result = manager._resolve_user_key("admin")

        assert result == 10
        client.users.get.assert_called_once_with(name="admin")

    def test_resolve_user_key_not_found(self) -> None:
        """Test _resolve_user_key returns None when user not found."""
        manager, client = self._create_manager()
        client.users.get.side_effect = NotFoundError("User not found")

        result = manager._resolve_user_key("nonexistent")

        assert result is None

    # _parse_expires_in() tests

    def test_parse_expires_in_days(self) -> None:
        """Test _parse_expires_in with days."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("30d")

        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (30 * 86400)
        assert result is not None
        assert abs(result - expected) < 60

    def test_parse_expires_in_weeks(self) -> None:
        """Test _parse_expires_in with weeks."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("2w")

        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (14 * 86400)
        assert result is not None
        assert abs(result - expected) < 60

    def test_parse_expires_in_months(self) -> None:
        """Test _parse_expires_in with months."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("3m")

        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (90 * 86400)
        assert result is not None
        assert abs(result - expected) < 60

    def test_parse_expires_in_years(self) -> None:
        """Test _parse_expires_in with years."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("1y")

        expected = int(datetime.now(tz=timezone.utc).timestamp()) + (365 * 86400)
        assert result is not None
        assert abs(result - expected) < 60

    def test_parse_expires_in_invalid(self) -> None:
        """Test _parse_expires_in with invalid format."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("invalid")

        assert result is None

    def test_parse_expires_in_case_insensitive(self) -> None:
        """Test _parse_expires_in is case insensitive."""
        manager, client = self._create_manager()

        result = manager._parse_expires_in("30D")

        assert result is not None
