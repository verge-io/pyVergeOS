"""Base resource manager providing CRUD operations."""

from __future__ import annotations

import builtins
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from pyvergeos.exceptions import FieldNotProjectedError, NotFoundError
from pyvergeos.filters import combine_filters, quote_value

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

T = TypeVar("T", bound="ResourceObject")
PT = TypeVar("PT")
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


PROJECTION_ALL = "all"

_ALIAS_RE = re.compile(r"\s+as\s+(\S+)\s*$")


def projection_alias(field: str) -> str:
    """Return the name a projection entry lands under in the response row.

    ``"machine#status#running as running"`` lands under ``"running"``;
    a plain column lands under itself.
    """
    match = _ALIAS_RE.search(field)
    return match.group(1) if match else field.strip()


def is_computed_projection(field: str) -> bool:
    """Is this projection entry something the server computes, not a column?

    ``fields=all`` returns columns. A traversal (``machine#status#running``),
    an aggregate (``count(members)``) or a sub-selection
    (``stats[reads,writes]``) is derived, so it is never part of ``all`` and
    has to be asked for by name -- ``all`` answers a sub-selected column with
    the bare foreign key instead, which is why ``storage_tier.read_ops``
    raised ``AttributeError`` under ``all``. Detected structurally rather
    than from a list of known names, so a new kind of computed entry is
    covered the day it is written.
    """
    stripped = field.strip()
    return (
        "#" in stripped  # traversal: machine#status#running
        or "(" in stripped  # aggregate: count(members)
        or "[" in stripped  # sub-selection: stats[reads,writes,rops]
        or projection_alias(stripped) != stripped  # anything explicitly aliased
    )


def expand_projection(
    fields: str | builtins.list[str] | None,
    defaults: builtins.list[str] | None,
) -> str | builtins.list[str] | None:
    """Make ``all`` an actual superset of a manager's default projection.

    ``all`` is resolved server-side to the resource's *own columns*. Anything
    a manager has the server compute rather than select is therefore absent
    from it -- aliased traversals (``machine#status#running as running``) and
    aggregates (``count(members) as member_count``) alike -- so a request for
    ``all`` silently comes back without ``running``, ``status`` and friends,
    and on ``nodes`` without even ``$key``. A caller who asked for *more*
    data got a *wrong* answer (issue #117).

    When ``all`` appears in the projection, the manager's computed entries and
    ``$key`` are appended to it, which the API accepts and which measurably
    restores the missing values. Entries the caller already named are left
    alone, so an explicit override still wins.

    Independently of ``all``, a caller who names one of the manager's alias
    names gets the manager's entry for it. ``fields=["$key","name","running"]``
    would otherwise select the ``vms`` table's own ``running`` column, which
    is null on every row, and the accessor would answer ``False`` for a
    running VM - the same defect reached without ``all``. Narrowing itself is
    still honoured: the projection stays exactly as wide as asked for.

    Args:
        fields: The caller's projection.
        defaults: The manager's default projection, or None.

    Returns:
        The projection to send, expanded only when ``all`` was requested.
    """
    if not fields:
        return fields

    names = split_fields(fields)
    computed_by_alias = {
        projection_alias(field): field for field in defaults or () if is_computed_projection(field)
    }

    # A caller who names an alias means the manager's field of that name, not
    # whatever bare column happens to share it. Asking vms for "running"
    # returns a real column that is null on every row, and vnets drops the
    # name entirely - either way the accessor answered False for a running
    # resource, which is issue #117 reached through a narrowed projection
    # rather than through 'all'. Send what the manager means by the name.
    resolved: builtins.list[str] = []
    translated = False
    for name in names:
        entry = computed_by_alias.get(name)
        if entry is not None and entry != name:
            resolved.append(entry)
            translated = True
        else:
            resolved.append(name)
    names = resolved

    if PROJECTION_ALL not in names:
        return names if translated else fields

    seen = {projection_alias(name) for name in names}
    extra: builtins.list[str] = []

    # $key is the resource's identity and ResourceObject.key depends on it,
    # yet several endpoints leave it out of 'all' - nodes and storage_tiers
    # among them, where .key then raised "Resource has no $key" for a plainly
    # persisted row. Ask for it unconditionally: endpoints that already carry
    # it tolerate the duplicate, and settings, which is keyed on 'key', simply
    # answers with both.
    if "$key" not in seen:
        seen.add("$key")
        extra.append("$key")

    for field in defaults or ():
        # 'all' already covers plain own-columns, so re-listing them only
        # bloats the URL. It covers nothing the server has to compute, and
        # it drops $key on at least the nodes endpoint.
        if not is_computed_projection(field):
            continue
        alias = projection_alias(field)
        if alias in seen:
            continue
        seen.add(alias)
        extra.append(field)

    return names + extra if extra else fields


#: Sentinel for "nothing supplied here", distinct from a legitimate ``None``.
_NO_VALUE: Any = object()


def display_map(mapping: Mapping[Any, Any], default: Any = _NO_VALUE) -> Callable[[Any], Any]:
    """Build a ``transform`` that renders a raw value through ``mapping``.

    Args:
        mapping: Raw value -> display value.
        default: Returned for an unmapped value. Omit to pass the raw value
            through unchanged, which is what the hand-written accessors did.

    Returns:
        A callable suitable for ``Projected(transform=...)``.
    """

    def _render(value: Any) -> Any:
        if default is _NO_VALUE:
            return mapping.get(value, value)
        return mapping.get(value, default)

    return _render


def split_reference(value: Any) -> tuple[str | None, str | int | None]:
    """Split a VergeOS reference into ``(table, key)``.

    Several columns hold a *polymorphic* reference -- a ``"table/key"``
    string such as ``"vms/39"`` naming both the table and the row, which is
    how ``tasks.create(owner=..., table=...)`` composes them. Others hold a
    plain key. A key is not always numeric either: recipes are keyed by name,
    so ``owner`` can be ``"vm_recipes/yottabyte-services-nas-winbind"``.

    Coercing any of those with ``int()`` raises ValueError, which is issue
    #126. This reports what is actually there instead:

    >>> split_reference("vms/39")
    ('vms', 39)
    >>> split_reference("vm_recipes/winbind-v1")
    ('vm_recipes', 'winbind-v1')
    >>> split_reference("deprecated")
    (None, 'deprecated')
    >>> split_reference("")
    (None, None)

    Args:
        value: The raw column value.

    Returns:
        ``(table, key)``. ``table`` is None when the value carries no table
        part; ``key`` is an int when it looks like one, and None when there
        is no value at all.
    """
    if value is None:
        return (None, None)
    if isinstance(value, bool):
        return (None, int(value))
    if isinstance(value, int):
        return (None, value)
    text = str(value).strip()
    if not text:
        return (None, None)
    table: str | None = None
    if "/" in text:
        table, _, text = text.partition("/")
        table = table or None
        if not text:
            return (table, None)
    try:
        return (table, int(text))
    except ValueError:
        return (table, text)


def reference_key(value: Any) -> str | int | None:
    """The key part of a reference: 39 from ``"vms/39"``. See split_reference."""
    return split_reference(value)[1]


def reference_table(value: Any) -> str | None:
    """The table part of a reference: ``"vms"`` from ``"vms/39"``, else None."""
    return split_reference(value)[0]


def epoch_utc(value: Any) -> Any:
    """Render a Unix timestamp as a timezone-aware UTC datetime.

    A ``transform`` for the several accessors that turn an epoch column into
    a ``datetime``. Pair it with ``falsy=None, null=None`` so that a missing
    or zero timestamp stays None rather than becoming 1970.
    """
    from datetime import datetime, timezone

    return datetime.fromtimestamp(int(value), tz=timezone.utc)


class Projected(Generic[PT]):
    """Declare an accessor and the projection entry behind it, together.

    Issue #117 was not that accessors guessed. It was that the fact
    *"``is_running`` comes from ``machine#status#running``"* was written down
    twice -- once in the manager's field list, once in the accessor's
    ``self.get("running", False)`` -- with nothing tying the two. Each fix was
    another sweep for copies of a hand-written pattern: ``all`` not carrying
    the traversal, a caller naming the alias and getting a bare column, an
    accessor with a two-argument read, then one with a one-argument read.

    Stating it once removes the class of defect rather than its instances::

        class Network(ResourceObject):
            is_running = Projected("machine#status#running as running", bool,
                                   default=False)

    The manager then derives its projection from the declarations instead of
    restating them, so the two cannot drift, and adding an accessor adds its
    field to every query that reads it.

    The read is performed in a fixed order, which is what lets the various
    hand-written bodies this replaces be reproduced exactly:

    1. ``require_projected(alias, default)``, or ``require_projected_any``
       when several aliases are given.
    2. If ``fallback`` is set and the value is falsy, re-read it from that
       plain field -- the ``x or self.get("y", 0)`` idiom.
    3. If ``falsy`` is set and the value is falsy, substitute it -- the
       ``x or 0`` idiom.
    4. If the value is None and ``null`` was given, return ``null``.
    5. Apply ``coerce``, then ``transform``.

    Note that ``coerce`` is applied to a null value unless ``null`` is given.
    That is deliberate: it is what the accessors being replaced did, and
    changing it here would alter behaviour silently rather than visibly.

    Args:
        entry: The projection entry -- ``"machine#status#running as running"``
            -- or a plain column name. A sequence of entries reads whichever
            was projected, for fields spelled differently by different
            endpoints.
        coerce: Applied to the value, typically ``str``, ``int`` or ``bool``.
        default: Returned when the field was requested but the server omitted
            it, as a traversal through a null polymorphic reference is.
        null: Returned uncoerced when the value is None. Omit to pass None
            to ``coerce``, which is what the accessors replaced here did.
        falsy: Substituted for any falsy value, reproducing ``x or 0``.
        fallback: Plain field read via ``get()`` when the value is falsy, for
            rows that carry the same fact under an embedded name.
        fallback_default: Default for that fallback read.
        transform: Applied last, for display maps and unit conversions.
        doc: Docstring for the generated attribute.
    """

    def __init__(
        self,
        entry: str | Sequence[str],
        coerce: Callable[[Any], Any] | None = None,
        *,
        default: Any = None,
        null: Any = _NO_VALUE,
        falsy: Any = _NO_VALUE,
        fallback: str | None = None,
        fallback_default: Any = None,
        transform: Callable[[Any], Any] | None = None,
        doc: str | None = None,
    ) -> None:
        entries = [entry] if isinstance(entry, str) else list(entry)
        if not entries:
            raise ValueError("Projected requires at least one projection entry")
        self.entries: builtins.list[str] = entries
        self.aliases: builtins.list[str] = [projection_alias(e) for e in entries]
        self.coerce = coerce
        self.default = default
        self.null = null
        self.falsy = falsy
        self.fallback = fallback
        self.fallback_default = fallback_default
        self.transform = transform
        self.name = self.aliases[0]
        self.__doc__ = doc

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Projected[PT]: ...

    @overload
    def __get__(self, obj: Any, objtype: type | None = None) -> PT: ...

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        if len(self.aliases) == 1:
            value = obj.require_projected(self.aliases[0], self.default)
        else:
            value = obj.require_projected_any(*self.aliases, default=self.default)
        if self.fallback is not None and not value:
            value = obj.get(self.fallback, self.fallback_default)
        if self.falsy is not _NO_VALUE and not value:
            value = self.falsy
        if value is None and self.null is not _NO_VALUE:
            return self.null
        if self.coerce is not None:
            value = self.coerce(value)
        if self.transform is not None:
            value = self.transform(value)
        return value

    def __set__(self, obj: Any, value: Any) -> None:
        """Write through to the backing mapping.

        Defined so this is a *data* descriptor and therefore always wins over
        the instance dictionary, matching the ``property`` it replaces. The
        value lands in the mapping, which is where ``ResourceObject``'s own
        ``__setattr__`` would have put it.
        """
        obj[self.name] = value


class ResourceObject(dict[str, Any]):
    """Dict subclass with attribute access and resource methods.

    Provides a dict-like object that also supports attribute access
    and common resource operations like refresh, save, and delete.

    Attribute assignment, item assignment, ``update()`` and ``setdefault()``
    all mark the field as modified; ``save()`` sends every modified field
    along with any keyword arguments.
    """

    def __init__(self, data: dict[str, Any], manager: ResourceManager[Any]) -> None:
        super().__init__(data)
        self._manager = manager
        self._dirty: set[str] = set()
        # What the request that produced this row asked the server for.
        # None when unknown, in which case require_projected() stays strict.
        # Type-checked rather than taken on trust, so a hand-built or mocked
        # manager degrades to "unknown" instead of to a truthy non-set.
        requested = getattr(manager, "_requested_aliases", None)
        self._requested: frozenset[str] | None = (
            requested if isinstance(requested, frozenset) else None
        )

    def __setitem__(self, key: str, value: Any) -> None:
        self.__dict__.setdefault("_dirty", set()).add(key)
        super().__setitem__(key, value)

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Merge values in, marking each one modified (issue #110).

        ``dict.update()`` writes straight to the backing mapping, so before
        this override a batch update marked nothing dirty and the following
        ``save()`` sent an empty ``PUT`` and reported success while
        persisting nothing.

        ``refresh()`` deliberately calls ``dict.update(self, ...)`` to load
        server state without dirtying it, which bypasses this override.
        """
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Insert ``default`` if absent, marking it modified (issue #110)."""
        if key not in self:
            self[key] = default
        return self[key]

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

    @classmethod
    def projected_entries(cls) -> builtins.list[str]:
        """Projection entries declared by this model's ``Projected`` fields.

        Lets a manager build its default projection from the declarations
        rather than restating them, so an accessor and the field list that
        feeds it cannot disagree (issue #125). Base classes first, in
        declaration order, de-duplicated.
        """
        seen: dict[str, None] = {}
        for klass in reversed(cls.__mro__):
            for value in vars(klass).values():
                if isinstance(value, Projected):
                    for entry in value.entries:
                        seen.setdefault(entry, None)
        return list(seen)

    def require_projected(self, name: str, default: Any = None) -> Any:
        """Return field ``name``, refusing to guess when it was not projected.

        Accessors built on this cannot conflate "the field says false" with
        "the field was never fetched".

        The test is what the request asked for, not merely whether the key
        came back. Most computed fields do come back null when there is
        nothing to report, but a traversal through a polymorphic reference
        is omitted outright when that reference is null, so absence alone
        would raise on a correctly projected row.

        Args:
            name: Field to read.
            default: Returned when the field was requested but the server
                omitted it, which a null polymorphic reference causes. This
                is the same value the ``self.get(name, default)`` call this
                replaced would have produced, so behaviour is unchanged for
                every case except the one being fixed.

        Returns:
            The stored value, which may be None.

        Raises:
            FieldNotProjectedError: If the field was never requested.
        """
        try:
            return self[name]
        except KeyError:
            pass
        # Absence is not on its own proof that the field was not requested.
        # A traversal through a *polymorphic* reference - ``creator#$display``
        # on tasks, where ``creator`` holds a ``table/key`` string - is
        # omitted entirely when that reference is null, rather than coming
        # back null. Measured on a live system: 8 such fields across 6
        # managers. So the row is only "not projected" if the request did not
        # ask for it; if it did, ``default`` is the answer, exactly as the
        # ``self.get(name, default)`` this replaced would have given.
        if self._requested is not None and name in self._requested:
            return default
        raise FieldNotProjectedError(name, type(self).__name__) from None

    def require_projected_any(self, *names: str, default: Any = None) -> Any:
        """Read the first of ``names`` that was projected.

        For accessors whose field is spelled differently depending on which
        projection produced the row -- ``volume_name`` or ``volume_display``,
        ``status`` or ``rstatus``. Requiring the first name alone would raise
        for a row that legitimately carries the second.

        Preserves the ``a or b`` chain these replaced: the first *truthy*
        present value wins, falling back to the first present value, so a
        genuine ``0`` or ``""`` is still reported.

        Args:
            *names: Candidate field names, in preference order.
            default: Returned when a name was requested but the server
                omitted it.

        Returns:
            The stored value, which may be None.

        Raises:
            FieldNotProjectedError: If none of ``names`` was requested.
        """
        present = [name for name in names if name in self]
        for name in present:
            value = self[name]
            if value:
                return value
        if present:
            return self[present[0]]
        if self._requested is not None and any(name in self._requested for name in names):
            return default
        raise FieldNotProjectedError(names[0], type(self).__name__)

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
        # Adopt the refetch's projection too. The rows are now whatever
        # get() asked for, so keeping the old record would have this object
        # disagree with an identical freshly-fetched one: a task refreshed
        # from a narrow projection carried the full default row yet still
        # raised for creator_display, which the server omits (issue #117).
        self._requested = getattr(result, "_requested", None)
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
        if not changes and not kwargs:
            # Nothing to write. An empty PUT is still a write - subject to
            # permissions, audit logging and any update side effects - for a
            # request the caller did not ask for (issue #111). Return current
            # state, which is what the write path would have returned.
            dirty.clear()
            return manager.get(self.key)
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

    #: The manager's default projection, when it has one. Declared here so
    #: that list()/get() can make a caller's ``all`` a true superset of it
    #: (issue #117). Subclasses that keep their defaults in a module constant
    #: should point this at that constant.
    _default_fields: builtins.list[str] | None = None

    #: Alias names sent to the server by the most recent ``_projection()``
    #: call. Captured by each ``ResourceObject`` at construction, which
    #: happens during the same request, so it is never read stale.
    _requested_aliases: frozenset[str] | None = None

    def __init__(self, client: VergeClient) -> None:
        self._client = client

    def _projection(
        self,
        fields: str | builtins.list[str] | None,
        *,
        defaults: builtins.list[str] | None = None,
    ) -> str | None:
        """Serialize a caller-supplied ``fields`` argument for the wire.

        The single place a projection becomes a request parameter, so that
        ``all`` is expanded into a true superset of this manager's default
        projection (issue #117) no matter which method built the request.
        Managers that assemble ``params`` themselves must use this rather
        than calling ``normalize_fields()`` directly; a tripwire enforces it.

        ``defaults`` is the projection that bare names and ``all`` expand
        against. Omit it to use this manager's ``_default_fields``. A query
        for a different endpoint must pass that endpoint's own columns
        (often ``Model.projected_entries()``). Expanding ``capacity``
        against ``ClusterTier`` rewrites it to ``status#capacity``, and on
        ``cluster_tier_status`` ``status`` is a string, so the alias comes
        back as ``'online'`` (issue #149). Pass ``[]`` when the names are
        already the columns to send and must not be rewritten.

        Args:
            fields: The caller's projection.
            defaults: Projection to expand against. None uses this
                manager's defaults.

        Returns:
            The wire-format ``fields`` value, or None.
        """
        basis = self._default_fields if defaults is None else defaults
        resolved = expand_projection(fields, basis)
        # Record the names this request asks the server for, so that objects
        # built from the response can tell "you never asked for this" from
        # "you asked, and the server had nothing to say" (issue #117).
        self._requested_aliases = (
            frozenset(projection_alias(name) for name in split_fields(resolved))
            if resolved
            else None
        )
        return normalize_fields(resolved)

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

        # Field selection. 'all' is expanded to include the manager's
        # computed entries, which the API would otherwise omit (issue #117).
        if fields:
            params["fields"] = self._projection(fields)

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

        When looking up by ``name`` this returns the **first** match
        (``limit=1``). VergeOS does not enforce unique names on every table, so
        if two resources share a name only one is returned and the other is not
        reported -- the duplicate is invisible to this call, not an error. When
        names may not be unique, look up by ``key``, or use
        ``list(filter="name eq ...")`` and decide how to handle more than one
        row yourself.

        Args:
            key: Resource $key (ID).
            name: Resource name (searched if ``key`` is not provided). Returns
                the first match if the name is not unique; see above.
            fields: Fields to return - a list of names or the API's
                comma-separated string.

        Returns:
            Resource object (the first match when searching by ``name``).

        Raises:
            NotFoundError: If resource not found.
            ValueError: If neither key nor name provided.
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = self._projection(fields)

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

    def _to_model_unprojected(self, data: dict[str, Any]) -> T:
        """Build a model from a response that carried no projection.

        Write responses are not query results. ``POST`` answers with a
        receipt -- ``$key``, ``$row``, ``dbpath``, ``location``, ``response``
        -- and ``PUT`` answers with ``{}``. Nothing in either was requested
        by a projection, so the object must not inherit the alias set left
        behind by whatever this manager fetched last: otherwise
        ``networks.list()`` followed by ``networks.update(...)`` would make
        the updated object answer ``is_running`` as ``False`` from a row that
        never contained it, which is issue #117 arriving by a side door.

        Clearing the record first makes such an object report the field as
        unfetched, the same answer it gives with no prior call, so the result
        does not depend on unrelated history.
        """
        self._requested_aliases = None
        return self._to_model(data)

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
        return self._to_model_unprojected(response)

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
        return self._to_model_unprojected(response)

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
