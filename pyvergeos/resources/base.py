"""Base resource manager providing CRUD operations."""

from __future__ import annotations

import builtins
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import combine_filters, quote_value

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

T = TypeVar("T", bound="ResourceObject")
SelfT = TypeVar("SelfT", bound="ResourceObject")


class ResourceObject(dict[str, Any]):
    """Dict subclass with attribute access and resource methods.

    Provides a dict-like object that also supports attribute access
    and common resource operations like refresh, save, and delete.

    Attribute or item assignment marks the field as modified; ``save()``
    sends every modified field along with any keyword arguments.
    """

    def __init__(self, data: dict[str, Any], manager: ResourceManager[Any]) -> None:
        super().__init__(data)
        self._manager = manager
        self._dirty: set[str] = set()

    def __setitem__(self, key: str, value: Any) -> None:
        # ponytail: only __setitem__/__setattr__ are tracked; dict.update()
        # and setdefault() bypass this. Override them if callers need it.
        self.__dict__.setdefault("_dirty", set()).add(key)
        super().__setitem__(key, value)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'") from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self[name] = value

    @property
    def key(self) -> int:
        """Resource primary key ($key).

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return int(k)

    def refresh(self: SelfT) -> SelfT:
        """Refresh this object in place with fresh data from the API.

        The object this is called on is updated, so wait loops like
        ``while not vm.running: vm.refresh()`` observe new state. Unsaved
        local modifications are discarded. Returns ``self``, so
        ``vm = vm.refresh()`` also remains correct.

        Returns:
            This object, updated with the latest data.
        """
        if self.key is None:
            raise ValueError("Cannot refresh resource without $key")
        result = self._manager.get(self.key)
        # Replace the backing mapping without marking fields dirty
        # (dict methods bypass the tracking __setitem__).
        dict.clear(self)
        dict.update(self, result)
        self.__dict__.setdefault("_dirty", set()).clear()
        return self

    def save(self, **kwargs: Any) -> ResourceObject:
        """Save changes to resource.

        Sends fields modified via attribute/item assignment since the object
        was loaded (or last saved), merged with ``kwargs``. Keyword arguments
        take precedence over locally modified fields.

        Args:
            **kwargs: Additional fields to update.

        Returns:
            Updated resource object.

        Example:
            >>> vm.cpu_cores = 4
            >>> vm.ram = 2048
            >>> vm = vm.save()  # PUT {"cpu_cores": 4, "ram": 2048}
        """
        result = self._save(**kwargs)
        return result  # type: ignore[no-any-return]

    def _save(self, **kwargs: Any) -> Any:
        """Persist locally modified fields plus ``kwargs``.

        Subclasses that override ``save()`` must delegate here. Modified fields
        are first run through the manager's ``_prepare_write_fields()`` alias
        translation, then when the manager has a typed ``update()`` they are
        sent as a raw PUT and only ``kwargs`` go through ``update()``.
        Tracking is reset only after the request succeeds.
        """
        if self.key is None:
            raise ValueError("Cannot save resource without $key")
        manager = self._manager
        dirty = self.__dict__.get("_dirty", set())
        changes = {k: self[k] for k in dirty if k in self and not k.startswith("$")}
        if changes:
            # Apply the manager's write-alias translation so attribute
            # assignment and typed update() behave identically (issue #97).
            changes = manager._prepare_write_fields(changes)
        if changes and type(manager).update is not ResourceManager.update:
            ResourceManager.update(manager, self.key, **changes)
            result = manager.update(self.key, **kwargs) if kwargs else manager.get(self.key)
        else:
            result = manager.update(self.key, **{**changes, **kwargs})
        dirty.clear()
        return result

    def delete(self) -> None:
        """Delete this resource."""
        self._manager.delete(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.get("name", "")
        return f"<{type(self).__name__} key={key} name={name!r}>"


class ResourceManager(Generic[T]):
    """Base class for resource managers.

    Provides standard CRUD operations and filtering for API resources.
    Subclasses should set `_endpoint` and optionally override `_to_model`.
    """

    _endpoint: str = ""

    def __init__(self, client: VergeClient) -> None:
        self._client = client

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[T]:
        """List resources with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments. Merged with ``filter``
                when both are supplied.

        Returns:
            List of resource objects.

        Raises:
            ValueError: If filter kwargs are supplied but every value is None,
                which would silently match every row (issue #96).
        """
        params: dict[str, Any] = {}

        # Merge explicit filter with shorthand kwargs (issue #96: kwargs were
        # silently dropped whenever a filter string was already present).
        combined_filter = combine_filters(filter, filter_kwargs)
        if combined_filter:
            params["filter"] = combined_filter

        # Field selection
        if fields:
            params["fields"] = ",".join(fields)

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
    ) -> T:
        """Get a single resource by key or name.

        Args:
            key: Resource $key (ID).
            name: Resource name (will search if key not provided).
            fields: List of fields to return.

        Returns:
            Resource object.

        Raises:
            NotFoundError: If resource not found.
            ValueError: If neither key nor name provided.
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"{self._endpoint}/{key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"{self._endpoint}/{key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            results = self.list(filter=f"name eq {quote_value(name)}", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"{self._endpoint} with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(self, **kwargs: Any) -> T:
        """Create a new resource.

        Args:
            **kwargs: Resource attributes.

        Returns:
            Created resource object.
        """
        response = self._client._request("POST", self._endpoint, json_data=kwargs)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")
        return self._to_model(response)

    def update(self, key: int, **kwargs: Any) -> T:
        """Update an existing resource.

        Args:
            key: Resource $key (ID).
            **kwargs: Attributes to update.

        Returns:
            Updated resource object.
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            # Fetch updated resource
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a resource.

        Args:
            key: Resource $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def action(self, key: int, action_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Execute an action on a resource.

        Args:
            key: Resource $key (ID).
            action_name: Name of the action (e.g., "poweron", "snapshot").
            **kwargs: Action parameters.

        Returns:
            Action response (often includes task information).
        """
        endpoint = f"{self._endpoint}/{key}?action={action_name}"
        response = self._client._request("PUT", endpoint, json_data=kwargs)
        if isinstance(response, dict):
            return response
        return None

    def _to_model(self, data: dict[str, Any]) -> T:
        """Convert API response to model object.

        Override in subclasses to return specific model types.
        """
        return ResourceObject(data, self)  # type: ignore[return-value]

    def _prepare_write_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Translate SDK-level field aliases to API field names for writes.

        ``ResourceObject._save()`` sends locally modified fields as a raw PUT,
        bypassing a manager's typed ``update()``. Managers whose ``update()``
        translates aliases (e.g. ``tier`` -> ``preferred_tier``) must apply the
        same translation here so attribute assignment plus ``save()`` and
        ``update()`` behave identically (issue #97). The default is a
        passthrough. Implementations must not mutate the input mapping.

        Args:
            fields: Field-value pairs as provided by the caller.

        Returns:
            Field-value pairs ready to send to the API.
        """
        return fields

    def iter_all(self, page_size: int = 100, **kwargs: Any) -> Iterator[T]:
        """Iterate through all resources, handling pagination automatically.

        Args:
            page_size: Number of items per page.
            **kwargs: Additional filter arguments.

        Yields:
            Resource objects.
        """
        offset = 0
        while True:
            batch = self.list(limit=page_size, offset=offset, **kwargs)
            if not batch:
                break
            yield from batch
            if len(batch) < page_size:
                break  # Last page
            offset += page_size

    def __iter__(self) -> Iterator[T]:
        """Iterate over all resources (uses iter_all with default page size)."""
        return self.iter_all()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(endpoint={self._endpoint!r})"
