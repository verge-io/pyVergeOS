"""vSAN query resource manager for journal, tier, and repair status."""

from __future__ import annotations

import builtins
import time
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError, VergeTimeoutError
from pyvergeos.resources.base import ResourceManager
from pyvergeos.resources.queries import QUERY_DEFAULT_FIELDS, QueryResult

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class VsanQueryManager(ResourceManager[QueryResult]):
    """Manager for vSAN diagnostic queries.

    Supports async POST-and-poll queries for vSAN health:
    journal status, tier status, and repair status.

    Examples:
        Check journal health::

            result = client.vsan_queries.journal_status()
            print(result.result)

        Check tier status::

            result = client.vsan_queries.tier_status()
            print(result.result)

        Check repair status for a node::

            result = client.vsan_queries.repair_status(node_key=1)
            print(result.result)
    """

    _endpoint = "vsan_queries"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> QueryResult:
        return QueryResult(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[QueryResult]:
        """List vSAN queries.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.

        Returns:
            List of QueryResult objects.
        """
        if fields is None:
            fields = QUERY_DEFAULT_FIELDS

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filter:
            params["filter"] = filter
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

    def get(  # type: ignore[override]
        self,
        key: str | int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> QueryResult:
        """Get a vSAN query by key.

        Args:
            key: Query $key (SHA1 string or integer).
            fields: List of fields to return.

        Returns:
            QueryResult object.

        Raises:
            NotFoundError: If query not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("key must be provided")

        if fields is None:
            fields = QUERY_DEFAULT_FIELDS

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)

        if response is None or not isinstance(response, dict):
            raise NotFoundError(f"vSAN query {key} not found")

        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Submit a new vSAN query.

        Args:
            query: Query type (e.g. "getjournalstatus").
            params: Query parameters (e.g. {"node": 1}).

        Returns:
            QueryResult object.
        """
        body: dict[str, Any] = {"query": query}
        if params:
            body["params"] = params

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from vSAN query creation")

        key = response.get("$key")
        if key is not None:
            return self.get(key)
        return self._to_model(response)

    def wait(
        self,
        key: str | int,
        timeout: float = 120,
        poll_interval: float = 1.0,
    ) -> QueryResult:
        """Poll a vSAN query until it completes or errors.

        Args:
            key: Query $key to poll.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Completed QueryResult.

        Raises:
            VergeTimeoutError: If query doesn't complete within timeout.
        """
        deadline = time.monotonic() + timeout
        while True:
            result = self.get(key)
            if result.status in ("complete", "error"):
                return result
            if time.monotonic() >= deadline:
                raise VergeTimeoutError(
                    f"vSAN query {key} did not complete within {timeout}s (status: {result.status})"
                )
            time.sleep(poll_interval)

    def run(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        timeout: float = 120,
        poll_interval: float = 1.0,
    ) -> QueryResult:
        """Submit a vSAN query and wait for completion.

        Args:
            query: Query type string.
            params: Query parameters.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Completed QueryResult.
        """
        result = self.create(query, params)
        return self.wait(result.key, timeout=timeout, poll_interval=poll_interval)

    def journal_status(
        self,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Get vSAN journal status.

        Args:
            timeout: Max seconds to wait for result.
            **params: Additional query parameters.

        Returns:
            Completed QueryResult with journal status.
        """
        return self.run(
            "getjournalstatus",
            params if params else None,
            timeout=timeout,
        )

    def tier_status(
        self,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Get vSAN tier status.

        Args:
            timeout: Max seconds to wait for result.
            **params: Additional query parameters.

        Returns:
            Completed QueryResult with tier status.
        """
        return self.run(
            "gettierstatus",
            params if params else None,
            timeout=timeout,
        )

    def repair_status(
        self,
        node_key: int,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Get vSAN repair status for a node.

        Args:
            node_key: Node key to check repair status for.
            timeout: Max seconds to wait for result.
            **params: Additional query parameters.

        Returns:
            Completed QueryResult with repair status.
        """
        return self.run(
            "getrepairstatus",
            {"node": node_key, **params},
            timeout=timeout,
        )
