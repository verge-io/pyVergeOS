"""Webhook resource manager for VergeOS notification integrations."""

from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Authorization type mappings (friendly name -> API value)
AUTH_TYPE_MAP = {
    "None": "none",
    "Basic": "basic",
    "Bearer": "bearer",
    "ApiKey": "apikey",
}

# Reverse mapping (API value -> friendly name)
AUTH_TYPE_DISPLAY = {
    "none": "None",
    "basic": "Basic",
    "bearer": "Bearer",
    "apikey": "API Key",
}

# Status mappings (API value -> friendly name)
STATUS_DISPLAY = {
    "queued": "Queued",
    "running": "Running",
    "sent": "Sent",
    "error": "Error",
}


# Default fields for webhook list operations
_DEFAULT_WEBHOOK_FIELDS = [
    "$key",
    "name",
    "type",
    "url",
    "headers",
    "authorization_type",
    "allow_insecure",
    "timeout",
    "retries",
]

# Default fields for webhook history list operations
_DEFAULT_HISTORY_FIELDS = [
    "$key",
    "webhook_url",
    "message",
    "status",
    "status_info",
    "last_attempt",
    "created",
]


class Webhook(ResourceObject):
    """Webhook URL configuration resource object.

    Represents a webhook URL configuration in VergeOS that can receive
    notifications when events occur.

    Properties:
        name: Webhook name (unique identifier).
        webhook_type: Webhook type (currently only 'custom').
        url: Destination URL for webhook payloads.
        headers: Dict of custom HTTP headers.
        headers_raw: Raw header string in "Name:Value" format.
        authorization_type: Auth method (none, basic, bearer, apikey).
        authorization_type_display: Friendly auth type name.
        is_insecure: True if insecure SSL connections are allowed.
        timeout: Request timeout in seconds (3-120).
        retries: Number of retry attempts (0-100).
    """

    @property
    def name(self) -> str:
        """Get webhook name."""
        return str(self.get("name", ""))

    @property
    def webhook_type(self) -> str:
        """Get webhook type (currently only 'custom')."""
        return str(self.get("type", "custom"))

    @property
    def url(self) -> str:
        """Get destination URL."""
        return str(self.get("url", ""))

    @property
    def headers(self) -> dict[str, str]:
        """Get headers as dictionary."""
        headers_raw = self.get("headers", "")
        if not headers_raw:
            return {}

        result: dict[str, str] = {}
        for line in str(headers_raw).split("\n"):
            line = line.strip()
            if line and ":" in line:
                # Split on first colon only
                parts = line.split(":", 1)
                if len(parts) == 2:
                    result[parts[0].strip()] = parts[1].strip()
        return result

    @property
    def headers_raw(self) -> str:
        """Get raw header string in 'Name:Value' format."""
        return str(self.get("headers", ""))

    @property
    def authorization_type(self) -> str:
        """Get authorization type (API value)."""
        return str(self.get("authorization_type", "none"))

    @property
    def authorization_type_display(self) -> str:
        """Get friendly authorization type name."""
        return AUTH_TYPE_DISPLAY.get(self.authorization_type, self.authorization_type)

    @property
    def is_insecure(self) -> bool:
        """Check if insecure SSL connections are allowed."""
        return bool(self.get("allow_insecure", False))

    @property
    def timeout(self) -> int:
        """Get request timeout in seconds."""
        return int(self.get("timeout", 5))

    @property
    def retries(self) -> int:
        """Get number of retry attempts."""
        return int(self.get("retries", 3))

    def send(self, message: str | dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Send a test/manual message to this webhook.

        Args:
            message: JSON message payload. Can be a JSON string or dict.
                     Defaults to a simple test message.

        Returns:
            Action response (may include task info).
        """
        from typing import cast

        manager = cast("WebhookManager", self._manager)
        return manager.send(self.key, message=message)

    def history(
        self,
        *,
        status: str | None = None,
        pending: bool = False,
        failed: bool = False,
        limit: int = 100,
    ) -> builtins.list[WebhookHistory]:
        """Get execution history for this webhook.

        Args:
            status: Filter by status (queued, running, sent, error).
            pending: If True, show only pending (queued/running) messages.
            failed: If True, show only failed (error) messages.
            limit: Maximum number of entries to return.

        Returns:
            List of WebhookHistory objects.
        """
        from typing import cast

        manager = cast("WebhookManager", self._manager)
        return manager.history(
            webhook_key=self.key,
            status=status,
            pending=pending,
            failed=failed,
            limit=limit,
        )

    def __repr__(self) -> str:
        return f"<Webhook key={self.get('$key', '?')} name={self.name!r} url={self.url!r}>"


class WebhookHistory(ResourceObject):
    """Webhook execution history resource object.

    Represents a webhook message delivery attempt and its status.

    Properties:
        webhook_key: Key of the parent webhook URL.
        status: Delivery status (API value).
        status_display: Friendly status name.
        status_info: Additional status/error information.
        message: Parsed message payload (if JSON).
        message_raw: Raw message string.
        is_pending: True if message is queued or running.
        is_sent: True if message was successfully sent.
        has_error: True if delivery failed.
        last_attempt_at: Datetime of last delivery attempt.
        created_at: Datetime when message was queued.
    """

    @property
    def webhook_key(self) -> int | None:
        """Get parent webhook URL key."""
        val = self.get("webhook_url")
        return int(val) if val is not None else None

    @property
    def status(self) -> str:
        """Get delivery status (API value)."""
        return str(self.get("status", ""))

    @property
    def status_display(self) -> str:
        """Get friendly status name."""
        return STATUS_DISPLAY.get(self.status, self.status)

    @property
    def status_info(self) -> str:
        """Get additional status/error information."""
        return str(self.get("status_info", ""))

    @property
    def message(self) -> dict[str, Any] | str | None:
        """Get parsed message payload (if JSON)."""
        raw = self.get("message")
        if not raw:
            return None
        try:
            result = json.loads(str(raw))
            if isinstance(result, dict):
                return result
            return str(raw)
        except (json.JSONDecodeError, TypeError):
            return str(raw)

    @property
    def message_raw(self) -> str:
        """Get raw message string."""
        return str(self.get("message", ""))

    @property
    def is_pending(self) -> bool:
        """Check if message is pending (queued or running)."""
        return self.status in ("queued", "running")

    @property
    def is_sent(self) -> bool:
        """Check if message was successfully sent."""
        return self.status == "sent"

    @property
    def has_error(self) -> bool:
        """Check if delivery failed."""
        return self.status == "error"

    @property
    def last_attempt_at(self) -> datetime | None:
        """Get datetime of last delivery attempt."""
        ts = self.get("last_attempt")
        if ts is None or ts == 0:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    @property
    def created_at(self) -> datetime | None:
        """Get datetime when message was queued."""
        ts = self.get("created")
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    def __repr__(self) -> str:
        return f"<WebhookHistory key={self.get('$key', '?')} status={self.status_display!r}>"


class WebhookManager(ResourceManager[Webhook]):
    """Manager for webhook URL configurations.

    Provides CRUD operations for webhook URL configurations and methods
    to send test messages and view delivery history.

    Example:
        >>> # List all webhooks
        >>> webhooks = client.webhooks.list()
        >>>
        >>> # Create a webhook
        >>> webhook = client.webhooks.create(
        ...     name="slack-alerts",
        ...     url="https://hooks.slack.com/services/xxx",
        ...     authorization_type="none"
        ... )
        >>>
        >>> # Send a test message
        >>> client.webhooks.send(webhook.key, message='{"text": "Hello!"}')
        >>>
        >>> # View delivery history
        >>> history = client.webhooks.history(webhook_key=webhook.key)
    """

    _endpoint = "webhook_urls"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Webhook:
        """Convert API response to Webhook object."""
        return Webhook(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        authorization_type: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Webhook]:
        """List webhooks with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            authorization_type: Filter by auth type (None, Basic, Bearer, ApiKey).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Webhook objects.
        """
        params: dict[str, Any] = {}
        filters: builtins.list[str] = []

        # Build filter from string
        if filter:
            filters.append(filter)

        # Filter by authorization type
        if authorization_type:
            api_auth_type = AUTH_TYPE_MAP.get(authorization_type, authorization_type.lower())
            filters.append(f"authorization_type eq '{api_auth_type}'")

        # Add filter kwargs
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        # Field selection
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(_DEFAULT_WEBHOOK_FIELDS)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Webhook:
        """Get a webhook by key or name.

        Args:
            key: Webhook $key (ID).
            name: Webhook name (exact match).
            fields: List of fields to return.

        Returns:
            Webhook object.

        Raises:
            NotFoundError: If webhook not found.
            ValueError: If neither key nor name provided.
        """
        field_list = fields or _DEFAULT_WEBHOOK_FIELDS

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(field_list)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Webhook with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Webhook with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=field_list, limit=1)
            if not results:
                raise NotFoundError(f"Webhook with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        url: str,
        *,
        headers: dict[str, str] | str | None = None,
        authorization_type: str = "None",
        authorization_value: str | None = None,
        allow_insecure: bool = False,
        timeout: int | None = None,
        retries: int | None = None,
    ) -> Webhook:
        """Create a new webhook URL configuration.

        Args:
            name: Webhook name (unique).
            url: Destination URL (must start with http:// or https://).
            headers: Custom HTTP headers as dict or "Name:Value" string.
            authorization_type: Auth method (None, Basic, Bearer, ApiKey).
            authorization_value: Auth credential value.
                - Basic: "username:password" (will be base64 encoded)
                - Bearer: token value
                - ApiKey: key value
            allow_insecure: Allow insecure SSL connections.
            timeout: Request timeout in seconds (3-120, default 5).
            retries: Number of retry attempts (0-100, default 3).

        Returns:
            Created Webhook object.

        Raises:
            ValidationError: If parameters invalid.
            ConflictError: If webhook with name already exists.
        """
        body: dict[str, Any] = {
            "name": name,
            "url": url,
        }

        # Process headers
        if headers:
            if isinstance(headers, dict):
                header_lines = [f"{k}:{v}" for k, v in headers.items()]
                body["headers"] = "\n".join(header_lines) + "\n"
            else:
                # String format
                body["headers"] = headers if headers.endswith("\n") else f"{headers}\n"

        # Authorization
        api_auth_type = AUTH_TYPE_MAP.get(authorization_type, authorization_type.lower())
        body["authorization_type"] = api_auth_type
        if authorization_value:
            body["authorization_value"] = authorization_value

        # Optional settings
        if allow_insecure:
            body["allow_insecure"] = True

        if timeout is not None:
            body["timeout"] = timeout

        if retries is not None:
            body["retries"] = retries

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch full object since POST response may not include all fields
        key = response.get("$key")
        if key is not None:
            return self.get(int(key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        url: str | None = None,
        headers: dict[str, str] | str | None = None,
        authorization_type: str | None = None,
        authorization_value: str | None = None,
        allow_insecure: bool | None = None,
        timeout: int | None = None,
        retries: int | None = None,
    ) -> Webhook:
        """Update a webhook configuration.

        Args:
            key: Webhook $key (ID).
            name: New webhook name.
            url: New destination URL.
            headers: New custom HTTP headers. Pass empty dict to clear.
            authorization_type: New auth method.
            authorization_value: New auth credential value.
            allow_insecure: New allow insecure setting.
            timeout: New request timeout.
            retries: New retry count.

        Returns:
            Updated Webhook object.

        Raises:
            NotFoundError: If webhook not found.
            ValidationError: If parameters invalid.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if url is not None:
            body["url"] = url

        if headers is not None:
            if isinstance(headers, dict):
                if headers:
                    header_lines = [f"{k}:{v}" for k, v in headers.items()]
                    body["headers"] = "\n".join(header_lines) + "\n"
                else:
                    body["headers"] = ""
            else:
                body["headers"] = headers if headers.endswith("\n") else f"{headers}\n"

        if authorization_type is not None:
            api_auth_type = AUTH_TYPE_MAP.get(authorization_type, authorization_type.lower())
            body["authorization_type"] = api_auth_type

        if authorization_value is not None:
            body["authorization_value"] = authorization_value

        if allow_insecure is not None:
            body["allow_insecure"] = allow_insecure

        if timeout is not None:
            body["timeout"] = timeout

        if retries is not None:
            body["retries"] = retries

        if not body:
            # No changes, just fetch current
            return self.get(key)

        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        if response is None or not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a webhook configuration.

        This also deletes any pending messages in the queue for this webhook.

        Args:
            key: Webhook $key (ID).

        Raises:
            NotFoundError: If webhook not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def send(
        self,
        key: int,
        *,
        message: str | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to a webhook.

        The message is queued for delivery. Use history() to check delivery status.

        Args:
            key: Webhook $key (ID).
            message: JSON message payload. Can be a JSON string or dict.
                     Defaults to a simple test message.

        Returns:
            Action response (may include task info).

        Raises:
            NotFoundError: If webhook not found.
        """
        # Process message
        if message is None:
            message_json = '{"text": "Webhook test from pyvergeos"}'
        elif isinstance(message, dict):
            message_json = json.dumps(message)
        else:
            message_json = message

        body = {"message": message_json}

        # Use action endpoint: webhook_urls/{id}/send
        endpoint = f"{self._endpoint}/{key}/send"
        response = self._client._request("POST", endpoint, json_data=body)
        if isinstance(response, dict):
            return response
        return None

    def history(
        self,
        key: int | None = None,
        *,
        webhook_key: int | None = None,
        webhook_name: str | None = None,
        status: str | None = None,
        pending: bool = False,
        failed: bool = False,
        limit: int = 100,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[WebhookHistory]:
        """Get webhook execution history.

        Args:
            key: History entry $key (ID) to get specific entry.
            webhook_key: Filter by webhook $key.
            webhook_name: Filter by webhook name.
            status: Filter by status (queued, running, sent, error).
            pending: If True, show only pending (queued/running) messages.
            failed: If True, show only failed (error) messages.
            limit: Maximum number of entries to return.
            fields: List of fields to return.

        Returns:
            List of WebhookHistory objects.
        """
        params: dict[str, Any] = {}
        filters: builtins.list[str] = []

        # Get specific entry by key
        if key is not None:
            filters.append(f"$key eq {key}")
        else:
            # Resolve webhook name to key
            resolved_webhook_key = webhook_key
            if webhook_name:
                webhook = self.get(name=webhook_name)
                resolved_webhook_key = webhook.key

            # Filter by webhook URL
            if resolved_webhook_key is not None:
                filters.append(f"webhook_url eq {resolved_webhook_key}")

            # Filter by status
            if status:
                api_status = status.lower()
                filters.append(f"status eq '{api_status}'")
            elif pending:
                filters.append("(status eq 'queued' or status eq 'running')")
            elif failed:
                filters.append("status eq 'error'")

            # Limit results
            params["limit"] = limit

        # Apply filters
        if filters:
            params["filter"] = " and ".join(filters)

        # Field selection
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(_DEFAULT_HISTORY_FIELDS)

        # Sort by created descending (newest first)
        params["sort"] = "-created"

        response = self._client._request("GET", "webhooks", params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [WebhookHistory(response, self)]

        return [WebhookHistory(item, self) for item in response]

    def get_history(self, key: int) -> WebhookHistory:
        """Get a specific webhook history entry by key.

        Args:
            key: History entry $key (ID).

        Returns:
            WebhookHistory object.

        Raises:
            NotFoundError: If history entry not found.
        """
        results = self.history(key=key, limit=1)
        if not results:
            raise NotFoundError(f"Webhook history entry with key {key} not found")
        return results[0]

    def list_pending(self, webhook_key: int | None = None, limit: int = 100) -> builtins.list[WebhookHistory]:
        """List pending webhook messages (queued or running).

        Args:
            webhook_key: Filter by webhook $key.
            limit: Maximum number of entries to return.

        Returns:
            List of WebhookHistory objects.
        """
        return self.history(webhook_key=webhook_key, pending=True, limit=limit)

    def list_failed(self, webhook_key: int | None = None, limit: int = 100) -> builtins.list[WebhookHistory]:
        """List failed webhook messages.

        Args:
            webhook_key: Filter by webhook $key.
            limit: Maximum number of entries to return.

        Returns:
            List of WebhookHistory objects.
        """
        return self.history(webhook_key=webhook_key, failed=True, limit=limit)
