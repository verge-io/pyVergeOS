"""Base resource manager providing CRUD operations."""

from __future__ import annotations

import builtins
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import combine_filters, quote_value

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

T = TypeVar("T", bound="ResourceObject")
SelfT = TypeVar("SelfT", bound="ResourceObject")


def serialize_list(value: str | builtins.list[str] | None, sep: str = ",") -> str | None:
    """Serialize a user-supplied multi-value parameter for the API.

    Accepts either the API's native delimiter-joined string or a sequence
    of values. A bare string passes through unchanged: joining it would
    iterate character by character (``",".join("$key,name")`` ->
    ``'$,k,e,y,,,n,a,m,e'``), which the API accepts and silently honours,
    corrupting the request (issue #101).

    An empty sequence serializes to ``""``, which callers use to clear a
    multi-value field, so it is deliberately not treated as "unset".

    Args:
        value: A string already in wire format, a sequence of values,
            or None.
        sep: Delimiter the API expects (``","`` or ``"\\n"``).

    Returns:
        The wire-format string, or None if ``value`` is None.

    Raises:
        TypeError: If ``value`` is a mapping, an unordered collection, or
            contains a non-string. Each of these would otherwise be
            serialized into a plausible-looking but wrong request rather
            than failing.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        raise TypeError(
            f"expected a string or a sequence of strings, not {type(value).__name__}; "
            "iterating a mapping yields its keys, which would be sent as the value"
        )
    if isinstance(value, (set, frozenset)):
        # Order is part of the value for several of these parameters - the
        # first entry of dnslist is the primary DNS server - and a set has
        # no defined order, so the wire value would vary run to run.
        raise TypeError(
            f"expected an ordered sequence, not {type(value).__name__}; "
            "pass a list so the order sent to the API is defined"
        )
    items = list(value)
    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"values must be strings, got {type(item).__name__}: {item!r}")
    return sep.join(items)


def normalize_fields(fields: str | builtins.list[str] | None) -> str | None:
    """Serialize a ``fields`` projection parameter.

    Accepts a sequence of field names or the API's comma-separated string.
    Empty values - including strings that contain no field names, such as
    ``","`` or ``"   "`` - mean "no projection requested" (issue #101).
    Passing those through would ask the API for a projection with no
    columns, which answers with a single ``{"$count": N}`` row instead of
    the requested resources: the silent-empty result #101 was filed for.

    Field names are cleaned exactly as :func:`split_fields` cleans them, so
    the string and sequence forms stay interchangeable.
    """
    names = split_fields(fields)
    if not names:
        return None
    return ",".join(names)


def split_fields(fields: str | builtins.list[str] | None) -> builtins.list[str]:
    """Split a ``fields`` projection into individual field names.

    The list counterpart of :func:`normalize_fields`, for the callers that
    must *augment* the projection (adding ``settings``, ``client_secret``
    and similar) before serializing it. Those callers cannot use
    ``normalize_fields()``, and ``list("$key,name")`` would split a
    caller-supplied string into single characters - the same silent
    corruption as ``",".join()`` (issue #101).

    Args:
        fields: A comma-separated string, a sequence of names, or None.

    Returns:
        A list of field names; empty when no projection was requested.

    Raises:
        TypeError: If ``fields`` is a mapping, or if any element is not a
            string. Iterating a mapping yields its keys, and coercing
            elements with ``str()`` would turn ``[1, 2]`` into the projection
            ``"1,2"`` - a plausible-looking but wrong request. Both must fail
            loudly rather than silently corrupt the query.
    """
    if not fields:
        return []
    if isinstance(fields, str):
        return [name.strip() for name in fields.split(",") if name.strip()]
    if isinstance(fields, Mapping):
        raise TypeError(
            f"fields must be a string or a sequence of field names, not {type(fields).__name__}"
        )
    names = []
    for name in fields:
        if not isinstance(name, str):
            raise TypeError(f"field names must be strings, got {type(name).__name__}: {name!r}")
        stripped = name.strip()
        # Empty entries are dropped here exactly as they are for the string
        # form, so ["$key", ""] and "$key," produce the same projection.
        if stripped:
            names.append(stripped)
    return names


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
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[T]:
        """List resources with optional filtering.

        Args:
            filter: OData filter string.
            fields: Fields to return - a list of names or the API's
                comma-separated string.
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
            params["fields"] = normalize_fields(fields)

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
        fields: str | builtins.list[str] | None = None,
    ) -> T:
        """Get a single resource by key or name.

        Args:
            key: Resource $key (ID).
            name: Resource name (will search if key not provided).
            fields: Fields to return - a list of names or the API's
                comma-separated string.

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
                params["fields"] = normalize_fields(fields)

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
