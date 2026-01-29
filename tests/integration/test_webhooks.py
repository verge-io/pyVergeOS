"""Integration tests for Webhook operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import time
import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.webhooks import Webhook


def unique_name(prefix: str = "pyvergeos-test") -> str:
    """Generate a unique name for test resources."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_webhook_name() -> str:
    """Generate a unique test webhook name."""
    return unique_name("pyvergeos-webhook")


@pytest.fixture
def test_webhook(live_client: VergeClient, test_webhook_name: str):
    """Create and cleanup a test webhook."""
    webhook = live_client.webhooks.create(
        name=test_webhook_name,
        url="https://httpbin.org/post",
        timeout=10,
        retries=2,
    )

    yield webhook

    # Cleanup
    try:  # noqa: SIM105
        live_client.webhooks.delete(webhook.key)
    except NotFoundError:
        pass  # Already deleted


@pytest.mark.integration
class TestWebhookListIntegration:
    """Integration tests for WebhookManager list operations."""

    def test_list_webhooks(self, live_client: VergeClient) -> None:
        """Test listing webhooks from live system."""
        webhooks = live_client.webhooks.list()

        # Should return a list (may be empty)
        assert isinstance(webhooks, list)

        # Each webhook should have expected properties
        for webhook in webhooks:
            assert hasattr(webhook, "key")
            assert hasattr(webhook, "name")
            assert hasattr(webhook, "url")
            assert hasattr(webhook, "timeout")
            assert hasattr(webhook, "retries")

    def test_list_webhooks_with_limit(self, live_client: VergeClient) -> None:
        """Test listing webhooks with limit."""
        webhooks = live_client.webhooks.list(limit=1)

        assert isinstance(webhooks, list)
        assert len(webhooks) <= 1

    def test_list_webhooks_with_auth_filter(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test listing webhooks with authorization type filter."""
        webhooks = live_client.webhooks.list(authorization_type="None")

        assert isinstance(webhooks, list)
        for webhook in webhooks:
            assert webhook.authorization_type == "none"


@pytest.mark.integration
class TestWebhookGetIntegration:
    """Integration tests for WebhookManager get operations."""

    def test_get_webhook_by_key(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test getting a webhook by key."""
        fetched = live_client.webhooks.get(test_webhook.key)

        assert fetched.key == test_webhook.key
        assert fetched.name == test_webhook.name

    def test_get_webhook_by_name(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test getting a webhook by name."""
        fetched = live_client.webhooks.get(name=test_webhook.name)

        assert fetched.key == test_webhook.key
        assert fetched.name == test_webhook.name

    def test_get_webhook_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent webhook."""
        with pytest.raises(NotFoundError):
            live_client.webhooks.get(name="non-existent-webhook-12345")


@pytest.mark.integration
class TestWebhookCRUDIntegration:
    """Integration tests for Webhook CRUD operations."""

    def test_create_and_delete_webhook(
        self, live_client: VergeClient, test_webhook_name: str
    ) -> None:
        """Test creating and deleting a webhook."""
        webhook = live_client.webhooks.create(
            name=test_webhook_name,
            url="https://httpbin.org/post",
            headers={"X-Test-Header": "test-value", "Content-Type": "application/json"},
            authorization_type="None",
            timeout=15,
            retries=3,
            allow_insecure=False,
        )

        try:
            assert webhook.name == test_webhook_name
            assert webhook.url == "https://httpbin.org/post"
            assert webhook.timeout == 15
            assert webhook.retries == 3
            assert "X-Test-Header" in webhook.headers
            assert webhook.headers["X-Test-Header"] == "test-value"
            assert webhook.authorization_type == "none"
            assert webhook.is_insecure is False

            # Verify it exists
            fetched = live_client.webhooks.get(webhook.key)
            assert fetched.key == webhook.key
        finally:
            # Cleanup
            live_client.webhooks.delete(webhook.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.webhooks.get(name=test_webhook_name)

    def test_create_webhook_with_bearer_auth(
        self, live_client: VergeClient, test_webhook_name: str
    ) -> None:
        """Test creating a webhook with Bearer auth."""
        webhook = live_client.webhooks.create(
            name=test_webhook_name,
            url="https://httpbin.org/post",
            authorization_type="Bearer",
            authorization_value="test-token-123",
        )

        try:
            assert webhook.authorization_type == "bearer"
            assert webhook.authorization_type_display == "Bearer"
        finally:
            live_client.webhooks.delete(webhook.key)

    def test_update_webhook(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test updating a webhook."""
        updated = live_client.webhooks.update(
            test_webhook.key,
            url="https://httpbin.org/anything",
            timeout=30,
            retries=5,
        )

        assert updated.url == "https://httpbin.org/anything"
        assert updated.timeout == 30
        assert updated.retries == 5

    def test_update_webhook_headers(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test updating webhook headers."""
        updated = live_client.webhooks.update(
            test_webhook.key,
            headers={"New-Header": "new-value"},
        )

        assert "New-Header" in updated.headers
        assert updated.headers["New-Header"] == "new-value"

    def test_update_webhook_auth_type(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test updating webhook auth type."""
        updated = live_client.webhooks.update(
            test_webhook.key,
            authorization_type="Bearer",
            authorization_value="new-token",
        )

        assert updated.authorization_type == "bearer"


@pytest.mark.integration
class TestWebhookSendIntegration:
    """Integration tests for webhook send operations."""

    def test_send_webhook_default_message(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test sending a webhook with default message."""
        result = live_client.webhooks.send(test_webhook.key)

        # Send returns None or task info
        assert result is None or isinstance(result, dict)

    def test_send_webhook_custom_message_dict(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test sending a webhook with custom dict message."""
        result = live_client.webhooks.send(
            test_webhook.key,
            message={"text": "Test message from pyvergeos", "source": "integration-test"},
        )

        assert result is None or isinstance(result, dict)

    def test_send_webhook_custom_message_string(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test sending a webhook with custom string message."""
        result = live_client.webhooks.send(
            test_webhook.key,
            message='{"custom": "json-string"}',
        )

        assert result is None or isinstance(result, dict)

    def test_send_via_object_method(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test sending via webhook object method."""
        result = test_webhook.send(message={"test": "object-method"})

        assert result is None or isinstance(result, dict)


@pytest.mark.integration
class TestWebhookHistoryIntegration:
    """Integration tests for webhook history operations."""

    def test_history_basic(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test getting webhook history."""
        # Send a message first
        live_client.webhooks.send(test_webhook.key, message={"test": "history"})

        # Wait for delivery
        time.sleep(3)

        history = live_client.webhooks.history(webhook_key=test_webhook.key)

        assert isinstance(history, list)
        assert len(history) >= 1

        # Verify history entry properties
        entry = history[0]
        assert entry.webhook_key == test_webhook.key
        assert entry.status in ("queued", "running", "sent", "error")
        assert entry.created_at is not None

    def test_history_via_object_method(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test getting history via webhook object method."""
        # Send a message first
        live_client.webhooks.send(test_webhook.key, message={"test": "object-history"})
        time.sleep(3)

        history = test_webhook.history(limit=5)

        assert isinstance(history, list)
        assert len(history) >= 1

    def test_get_history_entry(
        self, live_client: VergeClient, test_webhook: Webhook
    ) -> None:
        """Test getting a specific history entry."""
        # Send a message first
        live_client.webhooks.send(test_webhook.key, message={"test": "get-entry"})
        time.sleep(3)

        # Get history list
        history = live_client.webhooks.history(webhook_key=test_webhook.key)
        if not history:
            pytest.skip("No history entries available")

        # Get specific entry
        entry = live_client.webhooks.get_history(history[0].key)

        assert entry.key == history[0].key

    def test_list_pending(self, live_client: VergeClient) -> None:
        """Test listing pending webhook messages."""
        pending = live_client.webhooks.list_pending()

        assert isinstance(pending, list)
        for entry in pending:
            assert entry.is_pending is True

    def test_list_failed(self, live_client: VergeClient) -> None:
        """Test listing failed webhook messages."""
        failed = live_client.webhooks.list_failed()

        assert isinstance(failed, list)
        for entry in failed:
            assert entry.has_error is True


@pytest.mark.integration
class TestWebhookEdgeCasesIntegration:
    """Integration tests for webhook edge cases."""

    def test_webhook_with_special_chars_in_name(
        self, live_client: VergeClient
    ) -> None:
        """Test creating webhook with special characters in name."""
        name = unique_name("pyvergeos-test_webhook")

        webhook = live_client.webhooks.create(
            name=name,
            url="https://httpbin.org/post",
        )

        try:
            assert webhook.name == name
            # Verify can fetch by name
            fetched = live_client.webhooks.get(name=name)
            assert fetched.key == webhook.key
        finally:
            live_client.webhooks.delete(webhook.key)

    def test_webhook_with_insecure_flag(
        self, live_client: VergeClient, test_webhook_name: str
    ) -> None:
        """Test creating webhook with allow_insecure flag."""
        webhook = live_client.webhooks.create(
            name=test_webhook_name,
            url="https://self-signed.example.com/hook",
            allow_insecure=True,
        )

        try:
            assert webhook.is_insecure is True
        finally:
            live_client.webhooks.delete(webhook.key)
