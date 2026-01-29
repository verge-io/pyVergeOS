"""Unit tests for Webhook operations."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.webhooks import (
    AUTH_TYPE_DISPLAY,
    AUTH_TYPE_MAP,
    STATUS_DISPLAY,
    Webhook,
    WebhookHistory,
)

# =============================================================================
# Webhook Model Tests
# =============================================================================


class TestWebhook:
    """Unit tests for Webhook model."""

    def test_webhook_properties(self, mock_client: VergeClient) -> None:
        """Test Webhook property accessors."""
        data = {
            "$key": 1,
            "name": "test-webhook",
            "type": "custom",
            "url": "https://example.com/webhook",
            "headers": "Content-Type:application/json\nX-Source:VergeOS\n",
            "authorization_type": "bearer",
            "allow_insecure": False,
            "timeout": 10,
            "retries": 3,
        }
        webhook = Webhook(data, mock_client.webhooks)

        assert webhook.key == 1
        assert webhook.name == "test-webhook"
        assert webhook.webhook_type == "custom"
        assert webhook.url == "https://example.com/webhook"
        assert webhook.headers == {"Content-Type": "application/json", "X-Source": "VergeOS"}
        assert webhook.headers_raw == "Content-Type:application/json\nX-Source:VergeOS\n"
        assert webhook.authorization_type == "bearer"
        assert webhook.authorization_type_display == "Bearer"
        assert webhook.is_insecure is False
        assert webhook.timeout == 10
        assert webhook.retries == 3

    def test_webhook_default_values(self, mock_client: VergeClient) -> None:
        """Test Webhook default values for missing fields."""
        data = {"$key": 1}
        webhook = Webhook(data, mock_client.webhooks)

        assert webhook.name == ""
        assert webhook.webhook_type == "custom"
        assert webhook.url == ""
        assert webhook.headers == {}
        assert webhook.headers_raw == ""
        assert webhook.authorization_type == "none"
        assert webhook.authorization_type_display == "None"
        assert webhook.is_insecure is False
        assert webhook.timeout == 5
        assert webhook.retries == 3

    def test_webhook_auth_type_display_none(self, mock_client: VergeClient) -> None:
        """Test auth_type_display for none auth."""
        data = {"$key": 1, "authorization_type": "none"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.authorization_type_display == "None"

    def test_webhook_auth_type_display_basic(self, mock_client: VergeClient) -> None:
        """Test auth_type_display for basic auth."""
        data = {"$key": 1, "authorization_type": "basic"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.authorization_type_display == "Basic"

    def test_webhook_auth_type_display_bearer(self, mock_client: VergeClient) -> None:
        """Test auth_type_display for bearer auth."""
        data = {"$key": 1, "authorization_type": "bearer"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.authorization_type_display == "Bearer"

    def test_webhook_auth_type_display_apikey(self, mock_client: VergeClient) -> None:
        """Test auth_type_display for apikey auth."""
        data = {"$key": 1, "authorization_type": "apikey"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.authorization_type_display == "API Key"

    def test_webhook_is_insecure_true(self, mock_client: VergeClient) -> None:
        """Test is_insecure returns True when allow_insecure is set."""
        data = {"$key": 1, "allow_insecure": True}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.is_insecure is True

    def test_webhook_headers_parsing(self, mock_client: VergeClient) -> None:
        """Test headers are parsed correctly."""
        data = {"$key": 1, "headers": "Header1:Value1\nHeader2:Value2\n"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.headers == {"Header1": "Value1", "Header2": "Value2"}

    def test_webhook_headers_with_colon_in_value(self, mock_client: VergeClient) -> None:
        """Test headers with colon in value are parsed correctly."""
        data = {"$key": 1, "headers": "Authorization:Bearer token:with:colons\n"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.headers == {"Authorization": "Bearer token:with:colons"}

    def test_webhook_headers_empty_lines(self, mock_client: VergeClient) -> None:
        """Test headers with empty lines are parsed correctly."""
        data = {"$key": 1, "headers": "Header1:Value1\n\nHeader2:Value2\n"}
        webhook = Webhook(data, mock_client.webhooks)
        assert webhook.headers == {"Header1": "Value1", "Header2": "Value2"}

    def test_webhook_repr(self, mock_client: VergeClient) -> None:
        """Test Webhook string representation."""
        data = {"$key": 1, "name": "test-webhook", "url": "https://example.com/hook"}
        webhook = Webhook(data, mock_client.webhooks)

        repr_str = repr(webhook)
        assert "Webhook" in repr_str
        assert "key=1" in repr_str
        assert "test-webhook" in repr_str
        assert "https://example.com/hook" in repr_str


# =============================================================================
# WebhookHistory Model Tests
# =============================================================================


class TestWebhookHistory:
    """Unit tests for WebhookHistory model."""

    def test_webhook_history_properties(self, mock_client: VergeClient) -> None:
        """Test WebhookHistory property accessors."""
        now_ts = int(time.time())
        data = {
            "$key": 1,
            "webhook_url": 10,
            "message": '{"text": "Test message"}',
            "status": "sent",
            "status_info": "HTTP 200",
            "last_attempt": now_ts - 60,
            "created": now_ts - 120,
        }
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.key == 1
        assert history.webhook_key == 10
        assert history.message == {"text": "Test message"}
        assert history.message_raw == '{"text": "Test message"}'
        assert history.status == "sent"
        assert history.status_display == "Sent"
        assert history.status_info == "HTTP 200"
        assert history.is_pending is False
        assert history.is_sent is True
        assert history.has_error is False
        assert history.last_attempt_at is not None
        assert history.created_at is not None

    def test_webhook_history_status_queued(self, mock_client: VergeClient) -> None:
        """Test status properties for queued message."""
        data = {"$key": 1, "status": "queued"}
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.status == "queued"
        assert history.status_display == "Queued"
        assert history.is_pending is True
        assert history.is_sent is False
        assert history.has_error is False

    def test_webhook_history_status_running(self, mock_client: VergeClient) -> None:
        """Test status properties for running message."""
        data = {"$key": 1, "status": "running"}
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.status == "running"
        assert history.status_display == "Running"
        assert history.is_pending is True
        assert history.is_sent is False
        assert history.has_error is False

    def test_webhook_history_status_error(self, mock_client: VergeClient) -> None:
        """Test status properties for error message."""
        data = {"$key": 1, "status": "error", "status_info": "Connection refused"}
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.status == "error"
        assert history.status_display == "Error"
        assert history.is_pending is False
        assert history.is_sent is False
        assert history.has_error is True
        assert history.status_info == "Connection refused"

    def test_webhook_history_message_non_json(self, mock_client: VergeClient) -> None:
        """Test message property with non-JSON content."""
        data = {"$key": 1, "message": "Plain text message"}
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.message == "Plain text message"
        assert history.message_raw == "Plain text message"

    def test_webhook_history_message_empty(self, mock_client: VergeClient) -> None:
        """Test message property with empty content."""
        data = {"$key": 1, "message": ""}
        history = WebhookHistory(data, mock_client.webhooks)

        assert history.message is None
        assert history.message_raw == ""

    def test_webhook_history_webhook_key_none(self, mock_client: VergeClient) -> None:
        """Test webhook_key returns None when not set."""
        data = {"$key": 1}
        history = WebhookHistory(data, mock_client.webhooks)
        assert history.webhook_key is None

    def test_webhook_history_last_attempt_none(self, mock_client: VergeClient) -> None:
        """Test last_attempt_at returns None when not set."""
        data = {"$key": 1}
        history = WebhookHistory(data, mock_client.webhooks)
        assert history.last_attempt_at is None

    def test_webhook_history_last_attempt_zero(self, mock_client: VergeClient) -> None:
        """Test last_attempt_at returns None when 0."""
        data = {"$key": 1, "last_attempt": 0}
        history = WebhookHistory(data, mock_client.webhooks)
        assert history.last_attempt_at is None

    def test_webhook_history_created_at_none(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when not set."""
        data = {"$key": 1}
        history = WebhookHistory(data, mock_client.webhooks)
        assert history.created_at is None

    def test_webhook_history_repr(self, mock_client: VergeClient) -> None:
        """Test WebhookHistory string representation."""
        data = {"$key": 1, "status": "sent"}
        history = WebhookHistory(data, mock_client.webhooks)

        repr_str = repr(history)
        assert "WebhookHistory" in repr_str
        assert "key=1" in repr_str
        assert "Sent" in repr_str


# =============================================================================
# WebhookManager Tests
# =============================================================================


class TestWebhookManager:
    """Unit tests for WebhookManager."""

    def test_manager_endpoint(self, mock_client: VergeClient) -> None:
        """Test manager has correct endpoint."""
        assert mock_client.webhooks._endpoint == "webhook_urls"

    def test_list_webhooks(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing webhooks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "webhook-1", "url": "https://example.com/1"},
            {"$key": 2, "name": "webhook-2", "url": "https://example.com/2"},
        ]

        webhooks = mock_client.webhooks.list()

        assert len(webhooks) == 2
        assert webhooks[0].name == "webhook-1"
        assert webhooks[1].name == "webhook-2"

    def test_list_webhooks_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing webhooks returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        webhooks = mock_client.webhooks.list()
        assert webhooks == []

    def test_list_webhooks_with_auth_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing webhooks with authorization type filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "bearer-hook", "authorization_type": "bearer"}
        ]

        webhooks = mock_client.webhooks.list(authorization_type="Bearer")

        assert len(webhooks) == 1
        # Verify filter was applied
        call_args = mock_session.request.call_args
        assert "authorization_type eq 'bearer'" in call_args.kwargs.get("params", {}).get(
            "filter", ""
        )

    def test_get_webhook_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting webhook by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "test-webhook",
            "url": "https://example.com/hook",
        }

        webhook = mock_client.webhooks.get(1)

        assert webhook.key == 1
        assert webhook.name == "test-webhook"

    def test_get_webhook_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting webhook by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "test-webhook", "url": "https://example.com/hook"}
        ]

        webhook = mock_client.webhooks.get(name="test-webhook")

        assert webhook.name == "test-webhook"

    def test_get_webhook_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting non-existent webhook raises NotFoundError."""
        mock_session.request.return_value.status_code = 404
        mock_session.request.return_value.json.return_value = {"error": "Not found"}
        mock_session.request.return_value.text = "Not found"

        with pytest.raises(NotFoundError):
            mock_client.webhooks.get(999)

    def test_get_webhook_no_params(self, mock_client: VergeClient) -> None:
        """Test getting webhook without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.webhooks.get()

    def test_create_webhook(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a webhook."""
        # First call for POST, second for GET to fetch full object
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {  # GET response
                "$key": 1,
                "name": "new-webhook",
                "url": "https://example.com/hook",
                "timeout": 10,
                "retries": 3,
            },
        ]

        webhook = mock_client.webhooks.create(
            name="new-webhook",
            url="https://example.com/hook",
            timeout=10,
            retries=3,
        )

        assert webhook.name == "new-webhook"
        assert webhook.timeout == 10

    def test_create_webhook_with_headers_dict(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a webhook with headers as dict."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "hook", "url": "https://example.com", "headers": "X-Test:value\n"},
        ]

        mock_client.webhooks.create(
            name="hook",
            url="https://example.com",
            headers={"X-Test": "value"},
        )

        # Verify headers were sent in correct format - check POST call (index 1)
        # Index 0 is the system validation call
        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert "X-Test:value" in body.get("headers", "")

    def test_create_webhook_with_headers_string(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a webhook with headers as string."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "hook", "url": "https://example.com"},
        ]

        mock_client.webhooks.create(
            name="hook",
            url="https://example.com",
            headers="X-Test:value",
        )

        # Index 1 is the POST call (index 0 is system validation)
        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("headers", "").startswith("X-Test:value")

    def test_create_webhook_with_auth(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a webhook with bearer auth."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "hook", "url": "https://example.com", "authorization_type": "bearer"},
        ]

        mock_client.webhooks.create(
            name="hook",
            url="https://example.com",
            authorization_type="Bearer",
            authorization_value="my-token",
        )

        # Index 1 is the POST call (index 0 is system validation)
        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("authorization_type") == "bearer"
        assert body.get("authorization_value") == "my-token"

    def test_update_webhook(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a webhook."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "updated-webhook",
            "url": "https://example.com/hook",
            "timeout": 30,
        }

        webhook = mock_client.webhooks.update(1, timeout=30)

        assert webhook.timeout == 30

    def test_update_webhook_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a webhook with no changes returns current state."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "webhook",
            "url": "https://example.com",
        }

        webhook = mock_client.webhooks.update(1)

        assert webhook.key == 1

    def test_update_webhook_clear_headers(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a webhook to clear headers."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "webhook",
            "headers": "",
        }

        mock_client.webhooks.update(1, headers={})

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("headers") == ""

    def test_delete_webhook(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a webhook."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.webhooks.delete(1)

        # Verify DELETE was called
        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "webhook_urls/1" in call_args.kwargs.get("url", "")

    def test_send_webhook(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test sending a webhook message."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        mock_client.webhooks.send(1, message={"text": "Test message"})

        call_args = mock_session.request.call_args
        assert "webhook_urls/1/send" in call_args.kwargs.get("url", "")
        body = call_args.kwargs.get("json", {})
        assert "message" in body
        assert '"text": "Test message"' in body["message"]

    def test_send_webhook_default_message(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test sending a webhook with default message."""
        mock_session.request.return_value.json.return_value = None

        mock_client.webhooks.send(1)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert "pyvergeos" in body.get("message", "")

    def test_send_webhook_string_message(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test sending a webhook with string message."""
        mock_session.request.return_value.json.return_value = None

        mock_client.webhooks.send(1, message='{"custom": "json"}')

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("message") == '{"custom": "json"}'

    def test_history(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting webhook history."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "webhook_url": 10, "status": "sent", "created": now_ts},
            {"$key": 2, "webhook_url": 10, "status": "error", "created": now_ts - 60},
        ]

        history = mock_client.webhooks.history(webhook_key=10)

        assert len(history) == 2
        assert history[0].status == "sent"
        assert history[1].status == "error"

    def test_history_by_webhook_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting webhook history by webhook name."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 10, "name": "test-webhook"}],  # First call for get by name
            [{"$key": 1, "webhook_url": 10, "status": "sent"}],  # Second call for history
        ]

        history = mock_client.webhooks.history(webhook_name="test-webhook")

        assert len(history) == 1

    def test_history_pending(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting pending webhook history."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "status": "queued"},
        ]

        mock_client.webhooks.history(pending=True)

        # Verify filter was applied
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "queued" in params.get("filter", "")
        assert "running" in params.get("filter", "")

    def test_history_failed(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting failed webhook history."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "status": "error"},
        ]

        mock_client.webhooks.history(failed=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "error" in params.get("filter", "")

    def test_get_history(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting specific history entry."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "status": "sent"}
        ]

        entry = mock_client.webhooks.get_history(1)

        assert entry.key == 1
        assert entry.status == "sent"

    def test_get_history_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting non-existent history entry raises NotFoundError."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.webhooks.get_history(999)

    def test_list_pending(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_pending convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "status": "queued"},
        ]

        pending = mock_client.webhooks.list_pending()

        assert len(pending) == 1

    def test_list_failed(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_failed convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "status": "error"},
        ]

        failed = mock_client.webhooks.list_failed()

        assert len(failed) == 1


# =============================================================================
# Webhook Object Method Tests
# =============================================================================


class TestWebhookObjectMethods:
    """Unit tests for Webhook object methods."""

    def test_webhook_send(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test sending via webhook object."""
        mock_session.request.return_value.json.return_value = None

        data = {"$key": 1, "name": "test", "url": "https://example.com"}
        webhook = Webhook(data, mock_client.webhooks)

        webhook.send(message={"test": True})

        call_args = mock_session.request.call_args
        assert "webhook_urls/1/send" in call_args.kwargs.get("url", "")

    def test_webhook_history(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting history via webhook object."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "webhook_url": 1, "status": "sent"}
        ]

        data = {"$key": 1, "name": "test", "url": "https://example.com"}
        webhook = Webhook(data, mock_client.webhooks)

        history = webhook.history(limit=5)

        assert len(history) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "webhook_url eq 1" in params.get("filter", "")


# =============================================================================
# Auth Type and Status Mapping Tests
# =============================================================================


class TestMappings:
    """Unit tests for mapping constants."""

    def test_auth_type_map(self) -> None:
        """Test AUTH_TYPE_MAP contains all auth types."""
        assert "None" in AUTH_TYPE_MAP
        assert "Basic" in AUTH_TYPE_MAP
        assert "Bearer" in AUTH_TYPE_MAP
        assert "ApiKey" in AUTH_TYPE_MAP

    def test_auth_type_display(self) -> None:
        """Test AUTH_TYPE_DISPLAY contains all auth types."""
        assert "none" in AUTH_TYPE_DISPLAY
        assert "basic" in AUTH_TYPE_DISPLAY
        assert "bearer" in AUTH_TYPE_DISPLAY
        assert "apikey" in AUTH_TYPE_DISPLAY

    def test_status_display(self) -> None:
        """Test STATUS_DISPLAY contains all statuses."""
        assert "queued" in STATUS_DISPLAY
        assert "running" in STATUS_DISPLAY
        assert "sent" in STATUS_DISPLAY
        assert "error" in STATUS_DISPLAY
