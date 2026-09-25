Changelog
=========

All notable changes to pyvergeos will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

Fixed
^^^^^

- ``VM.hotplug_drive()`` rejects ``media`` other than ``disk`` and
  interfaces other than ``virtio`` and ``virtio-scsi`` before creating
  a drive. If the hotplug action is still rejected, ``hotplug_drive()``
  and ``hotplug_nic()`` delete the device they created and re-raise, so
  a failed call does not leave an offline drive or NIC on the VM.
  (#169)

- ``VolumeAntivirusManager`` documents that VergeOS creates the
  per-volume antivirus row with the volume. Examples lead with
  ``get()`` and ``update()``. ``create()`` updates that row when one
  already exists, and does the same if a POST hits the unique
  constraint. (#170)

- ``VMSnapshotManager.restore(..., power_on=True)`` and
  ``VMSnapshot.restore(power_on=True)`` power the restored VM on.
  Clone mode reads the new VM key from ``response.vmkey`` (VergeOS
  returns ``{"response": {"vmkey": "..."}}``) and still accepts
  top level ``$key`` or ``key``. In place restore
  (``replace_original=True``) powers on the original VM even when the
  action body is empty. A failed power on POST is raised instead of
  ignored. (#172)

- ``VMSnapshotManager``, ``DriveManager``, and ``NICManager`` require the
  row's ``machine`` to equal the VM in ``get(key)``. ``update(key)``,
  ``delete(key)``, and ``VMSnapshotManager.restore(key)`` use that check
  and raise ``NotFoundError`` when the key belongs to another VM, before
  sending a write. ``list()`` was already filtered by machine. (#168)

- ``NetworkAlias``, ``NetworkAliasManager``, and
  ``NetworkAliasManager.create()`` describe router IP aliases
  (``vnet_addresses`` rows with ``type: ipalias``): extra addresses on
  the network's router. They are not the ``vnet_rule_aliases`` that a
  firewall rule's ``alias:<name>`` syntax resolves. This SDK has no
  manager for ``vnet_rule_aliases`` yet. Measured on VergeOS 26.1.8.
  (#155)

- ``TaskScriptManager.delete()`` documents that deleting a script also
  deletes its associated tasks. The previous note said scripts with
  associated tasks cannot be deleted, which the platform does not
  enforce. Measured on VergeOS 26.1.8. (#155)

- ``TagCategory.delete()`` and ``TagCategoryManager.delete()`` document
  that deleting a category also deletes every tag in it and every
  assignment of those tags. VergeOS does not require the category to be
  empty; ``DELETE tag_categories/<key>`` cascades. The previous notes
  said to delete tags first, which read as a refusal the platform does
  not enforce. Measured on VergeOS 26.1.8. (#154)

- ``ResourceRule.resource_group_key`` and ``Device.resource_group_key``
  return the resource group UUID as ``str | None``. Both properties
  called ``int()`` on ``resource_group``, which raised ``ValueError``
  for every real rule because resource groups are keyed by UUID. (#151)

- ``SnapshotProfilePeriodManager.create()``, ``update()`` /
  ``save()``, and ``SnapshotProfile.add_period()`` no longer accept
  ``skip_missed``. ``snapshot_profile_periods`` has no such column;
  VergeOS accepts the name and drops it, so the write looked
  successful and ``SnapshotProfilePeriod.skip_missed`` always read
  false. The property and the default field list drop it too.
  Passing it to ``update()`` or ``save()`` raises ``ValueError``.
  The other period write fields match columns measured on VergeOS
  26.1.8. (#139)

- ``VM.hotplug_drive()`` and ``VM.hotplug_nic()`` sent the create spec
  (``name``, ``disksize``, ``interface``, and so on) as the action params.
  VergeOS ``hotplugdrive`` and ``hotplugnic`` attach an existing device and
  require its key as ``device``, so both raised
  ``ValidationError: Device is a required parameter``. Each method now
  creates the drive or NIC, then posts the action with
  ``params: {"device": <key>}``. ``hotplug_drive(size=...)`` still takes
  bytes and must be a positive whole number of GiB, because the drive is
  created through ``drives.create(size_gb=...)``. Measured on VergeOS
  26.1.8. (#150)

- ``ClusterTier.get_status()`` read ``capacity``, ``used``, ``used_pct``,
  ``redundant``, ``encrypted`` and ``working`` as the string ``'online'``.
  ``get_tier_status()`` expanded those columns through ``ClusterTier``'s
  ``status#`` joins, and on ``cluster_tier_status`` ``status`` is a plain
  string, so every join came back as ``'online'``. ``capacity_bytes``,
  ``used_bytes`` and ``used_percent`` then raised ``ValueError``, and the
  redundancy flags were truthy strings. Status, stats and history queries
  now project the columns of the endpoint they call. (#149)


[1.7.1] - 2026-09-24
--------------------

Fixed
^^^^^

- ``VMSnapshotManager.create(retention=0)`` now sends ``expires: 0`` so the
  platform stores a never-expiring snapshot. Omitting ``expires`` previously
  let VergeOS default to +72 hours, contradicting the documented "use 0 for
  never expires" behaviour (and ``VMSnapshot.never_expires``, which already
  treated ``expires == 0`` as never). Measured on VergeOS 26.1.8. (#146)

- ``VMSnapshotManager.create()`` rejects a negative ``retention`` (and
  ``None``) instead of storing ``expires: 0``. Omitting ``retention`` still
  defaults to 24 hours. (#146)

- ``VMSnapshot.restore()`` now delegates to ``VMSnapshotManager.restore()``,
  which resolves ``snap_machine`` (a machine key) to the snapshot VM before
  posting to ``vm_actions``. The object method previously posted the machine
  key as a VM key, which raised ``NotFoundError`` and could clone the wrong
  VM if keys later collided. (#147)


[1.7.0] - 2026-09-24
--------------------

Fixed
^^^^^

- ``PhysicalDriveManager`` node scoping no longer filters on a nonexistent
  ``node`` column (which silently returned ``[]`` for every node). It now
  resolves ``nodes.machine`` → ``machine_drives`` → ``parent_drive`` filters,
  raises ``NotFoundError`` for a missing node, and projects
  ``parent_drive#machine#name as node_name`` in the default field set so
  identical hardware across nodes is distinguishable. Verified against a live
  VergeOS 26.1.8 lab. (#143)

- ``auth_sources.update()`` no longer claims that ``settings`` are "merged
  with existing". They are not: the API replaces the stored settings document
  wholesale, so a partial write deletes every key it omits. Measured on
  VergeOS 26.1.8, updating a source with ``settings={"scope": "openid"}``
  leaves exactly that one key behind -- ``client_id``, ``client_secret`` and
  the endpoints are gone, no error is raised, and the next SSO login simply
  fails. The client secret usually cannot be read back from the identity
  provider, so the configuration has to be rebuilt by hand.

  Anyone following the old docstring to change one field was destroying a
  working SSO configuration. The docstring now says the document is replaced
  in full and that omitted keys are deleted, and the manager and module
  examples no longer demonstrate the partial write that causes it. Behaviour
  is unchanged -- this was always what the API did. (#142)

Added
^^^^^

- ``auth_sources.update(..., merge_settings=True)`` gives the merge semantics
  the docstring used to promise: the SDK reads the current document with
  ``get(key, include_settings=True)``, shallow-merges your keys on top, and
  writes the result back, so changing ``scope`` alone keeps the client
  credentials. It requires ``settings`` (raising ``ValueError`` otherwise),
  costs one extra API call, and is read-modify-write rather than atomic -- a
  concurrent write landing between the read and the write is lost. The default
  remains ``False``, preserving replace semantics for existing callers. (#142)

Docs
^^^^

- ``AuthSource.settings`` documents that the server injects a ``debug`` key
  into the stored document that was never sent, so a round-trip comparison
  against what you wrote reports drift that is not there, and that the
  property is only populated when the source was fetched with
  ``include_settings=True``. (#142)


[1.6.1] - 2026-09-23
--------------------

Fixed
^^^^^

- ``cloud_snapshots.create(wait=True)`` now actually waits. Snapshot creation
  is not backed by a task row -- the POST response carries no ``task`` key and
  the row's ``task`` field stays null -- so the old code, which waited only
  when a task key was present, never waited at all: ``wait=True`` returned
  immediately with a snapshot still ``building`` and a stale ``status``. It now
  polls the snapshot row until it reports a settled status -- reading the raw
  field so a not-yet-populated status right after the POST is treated as still
  in progress rather than defaulting to ``normal`` and returning early --
  honouring ``wait_timeout`` (raising ``VergeTimeoutError`` on expiry) and
  returning the snapshot fetched fresh, so its ``status`` reflects reality.
  ``wait=False`` behaviour is unchanged. (#133)

Docs
^^^^

- ``ClusterStatus.can_lose_one_node()`` no longer describes itself as
  "conservative". It divides ``online_ram`` evenly across ``online_nodes``,
  but the real worst case is losing the *largest* node, so on a cluster of
  unequal nodes it errs toward True, in the unsafe direction, which is the
  opposite of what "conservative" promises. Two nodes of 68352 and 69120 MB
  give an even-spread ceiling of 68736 MB while only 68352 MB survives losing
  the larger one, so any ``used_ram`` in between reported True for a load the
  survivor could not hold.

  This is a wording fix, not a logic change: ``cluster_status`` exposes only
  aggregates, so the method cannot compute a worst case from its own data and
  even-spread is the best available at that layer. The docstring now states
  that it is an optimistic approximation, that a True is not an N-1 guarantee
  on unevenly sized clusters, and shows the per-node recipe over
  ``Node.vm_ram_mb`` for callers gating a real drain. Two tests pin the
  optimistic window so the behaviour and the caveat cannot drift apart. The
  1.5.0 entry above was corrected to match. (#135)

[1.6.0] - 2026-09-23
--------------------

Added
^^^^^

- ``cloud_snapshots.create()`` can now take ``include_tags``, ``exclude_tags``
  and ``quiesce_tags`` to create a **partial (tag-scoped) system snapshot** --
  capture only, or all-but, the VMs carrying the given tags, a VergeOS 26.1
  feature that was previously unreachable from the SDK. Tags may be given as a
  ``$key``, a name, or a Tag object; names are resolved to keys (an ambiguous
  name raises rather than guessing, since names are unique only within a
  category). ``include_tags`` and ``exclude_tags`` are mutually exclusive, and
  ``quiesce_tags`` requires one of them. A create with none of these is a full
  snapshot exactly as before. (#129)

[1.5.0] - 2026-09-23
--------------------

Added
^^^^^

- ``cluster_status`` manager (``client.cluster_status`` and, scoped,
  ``cluster.cluster_status``) exposing the ``cluster_status`` table -- the
  live per-cluster node/RAM/core capacity figures behind an N-1 capacity
  pre-check. Previously reachable only through a private ``client._request()``.
  ``ClusterStatus.can_lose_one_node()`` provides an even-spread
  approximation. (#127, wording corrected in 1.6.1 per #135)

- ``machine_drive_stats`` manager (``client.machine_drive_stats`` and, scoped,
  ``drive.drive_stats``) exposing per-drive IO counters. It addresses rows by a
  filter on ``parent_drive``; path-key access (``machine_drive_stats/<n>``)
  returns the row whose own ``$key`` is ``n``, which belongs to a different
  drive, and previously reported another drive's counters -- e.g. writes on a
  VM that had never booted. ``MachineDriveStats.has_booted`` reports whether the
  guest has issued disk writes, the reliable signal that it actually booted
  rather than merely powering on. (#128)

Notes
^^^^^

- The ``machine_nic_stats`` manager referenced in #128 already existed; only
  ``machine_drive_stats`` was missing. Both scoped stats managers now default
  ``list()`` to their projection, so a bare ``list()`` returns populated rows
  rather than only ``$key``.


[1.4.0] - 2026-09-23
--------------------

Added
^^^^^

- ``Projected``, a descriptor that declares an accessor and the projection
  entry that feeds it in one place, plus ``ResourceObject.projected_entries()``
  so a manager derives its default projection from those declarations instead
  of restating them. Adding an accessor now adds its field to every query that
  reads it. See :doc:`contributing`. (#125)

- ``display_map()`` and ``epoch_utc()`` transforms, and
  ``split_reference()`` / ``reference_key()`` / ``reference_table()`` for
  reading ``"table/key"`` references. (#125, #126)

- ``Task.owner_table`` was already present; ``TaskEvent.owner_key`` now
  reports the key it previously discarded. (#126)

Fixed
^^^^^

- Four accessors declared ``-> int`` coerced with ``int()`` on columns that
  hold a polymorphic reference (``"vms/39"``), a name-keyed reference
  (``"vm_recipes/winbind-v1"``) or a plain non-numeric value
  (``"deprecated"``, ``""``). Reading them raised ``ValueError`` on ordinary
  rows, so iterating alarms or tasks crashed on the first one::

      for alarm in client.alarms.list():
          print(alarm.owner_key)      # ValueError before this release

  ``alarms.owner_key``, ``alarms.alarm_type_key``, ``alarms.sub_owner``,
  ``tasks.owner_key``, ``tasks.creator_key`` and
  ``task_schedules.creator_key`` now report the key part of the reference.
  ``task_events.owner_key`` returned ``None`` for these rather than raising,
  discarding the key; it now reports it. (#126)

Changed
^^^^^^^

- **Type change.** The accessors above widen from ``int | None`` to
  ``str | int | None``, because a VergeOS key is not always numeric. Numeric
  references are unaffected -- ``39`` and ``"27"`` still read as ``int`` --
  and an absent column still reads as ``None``. Only values that previously
  raised behave differently. (#126)

- Every accessor for a computed field is now declared with ``Projected``
  rather than written by hand. This is a refactor: behaviour is unchanged,
  verified by comparing each accessor against the implementation it replaced
  across present, null, empty, falsy, absent-but-requested and
  never-requested values, and by checking that every manager's projection is
  unchanged in content. (#125)

  Contributors adding an accessor should read the new section in
  :doc:`contributing`; a test enforces that no ``@property`` calls
  ``require_projected``.

[1.3.0] - 2026-09-23
--------------------

Added
^^^^^

- ``FieldNotProjectedError``, raised when an accessor is asked for a field
  the request never fetched. Exported from ``pyvergeos`` and documented in
  :doc:`error_handling`. It is deliberately **not** an ``AttributeError``,
  so ``getattr(vm, "is_running", None)`` and ``hasattr(vm, "is_running")``
  propagate it rather than quietly answering ``None``/``False``; an
  ``AttributeError`` subclass would be swallowed by ``ResourceObject``'s
  dict attribute fallback. Use ``"running" in vm`` for a non-raising check.
  (#117)

Changed
^^^^^^^

- **Behaviour change.** An accessor whose backing field was not fetched now
  raises ``FieldNotProjectedError`` instead of returning ``False``, ``""``,
  ``0`` or ``"unknown"``. This affects callers that narrow ``fields`` and
  then read ``is_running``, ``status``, ``member_count`` and similar: they
  previously received a silently wrong answer.

  A wrong answer in this direction is the dangerous one - ``is_running`` is
  exactly the guard placed in front of a destructive operation, and a
  storage tier reported as ``"Offline"`` with zero capacity invites action
  on a healthy tier.

  No signatures changed, and the default projection is unaffected. To get a
  usable answer, use the manager's default fields, pass ``fields=["all"]``,
  or name the field - all three now agree::

      vm = client.vms.get(name="web-01")
      vm = client.vms.get(name="web-01", fields=["all"])
      vm = client.vms.get(name="web-01", fields=["$key", "running"])

  Accessors that can still answer from another fetched field keep their
  tolerant behaviour - ``device_type_display`` falls back to the
  ``device_type`` column, ``size_gb`` to ``disksize``. (#117)

- Accessors declared ``-> str | None`` now return a ``str``. Several
  returned whatever the API sent, so ``permission.identity_name`` answered
  the integer ``1`` where its own annotation promised text. Affects 32
  accessors; compare against ``"1"`` rather than ``1``. (#117)

Fixed
^^^^^

- ``fields=["all"]`` is no longer a silently lossy projection. ``all``
  resolves server-side to a resource's *own columns*, so nothing the server
  computes came back with it: aliased traversals
  (``machine#status#running as running``), aggregates
  (``count(members) as member_count``) and sub-selections
  (``stats[reads,writes]``) alike, and on ``nodes`` and ``storage_tiers`` not
  even ``$key``. A running VM read back under ``all`` reported
  ``is_running is False``, and ``node.key`` raised "Resource has no $key" for
  a plainly persisted node. ``all`` is now expanded with the manager's
  computed entries and ``$key``. (#117)

- Naming a field no longer selects the wrong one.
  ``fields=["$key", "name", "running"]`` selected the ``vms`` table's own
  ``running`` column, which is null on every row, so ``is_running`` answered
  ``False`` for a running VM. A projection entry matching one of the
  manager's alias names now resolves to the manager's entry for it.
  Narrowing is still honoured and is never widened. (#117)

- An object built from a write response no longer inherits the projection of
  whatever the manager last queried. ``POST`` answers with a receipt and
  ``PUT`` with ``{}``, so ``networks.list()`` followed by
  ``networks.update(...)`` produced an object that answered ``is_running`` as
  ``False`` from a row that never contained ``running`` - an answer that
  depended on unrelated earlier calls. (#117)

- ``refresh()`` adopts the refetched projection, so a refreshed object no
  longer disagrees with an identically fetched one. (#117)

- A field the server omits because a *polymorphic* reference is null - such
  as ``creator#$display`` on a task with no creator - is reported as its
  default rather than as unfetched. Absence alone is not proof that a field
  was not requested. (#117)

[1.2.8] - 2026-09-22
--------------------

Fixed
^^^^^

- ``fields="$key,name"`` no longer silently destroys the projection.
  ``fields`` was typed as a list but every call site serialised it with
  ``",".join(fields)``; a caller-supplied string - the API's own native
  format - was joined character by character (``'$,k,e,y,,,n,a,m,e'``),
  which the API accepted and answered with rows containing no usable
  fields. All 272 call sites now serialise through ``normalize_fields()``,
  which accepts a list of names or a comma-separated string, and the
  ``fields`` signatures were widened to match. The same footgun corrupted
  write-path sequence parameters (``ip_allow_list``/``ip_deny_list`` on API
  keys, ``valid_users``/``valid_groups``/``admin_users``/``admin_groups``/
  ``allowed_hosts``/``denied_hosts`` on CIFS shares, ``include``/``exclude``
  on volume syncs, ``dns_servers`` on networks); those now serialise through
  ``serialize_list()``, which passes strings through unchanged. An AST
  tripwire test fails CI if any function joins a caller-supplied parameter
  directly. (#101)
- The ``name`` search in ``tasks``, ``task_scripts``, ``task_schedules``
  and ``cloudinit_files`` no longer fails open for all-wildcard patterns.
  These managers carried a hand-rolled workaround that stripped ``*``/``?``
  and used a ``ct`` contains match; a name of ``"*"`` (or ``"?"``) stripped
  to an empty search term and appended no condition at all, returning every
  row - the fail-open shape of #96 - and ``name="Backup*"`` matched as a
  case-insensitive contains (also matching ``Nightly Backup``). All four now
  share the wildcard translation, so prefix patterns match prefixes,
  matching is case-sensitive, and a condition is always sent. Ported from
  the parallel fix in PR #104. (#103)
- Wildcard and list filter shorthands no longer emit operators VergeOS
  rejects. ``build_filter()`` and ``Filter`` produced ``like`` (from
  ``name="web*"``) and ``in`` (from ``status=[...]``), neither of which is
  in the platform's filter grammar - every such filter failed with HTTP 422
  "Invalid argument". Wildcards now translate to supported operators
  (``foo*`` -> ``bw``, ``*foo`` -> ``ew``, ``*foo*`` -> ``cs``, complex
  patterns -> anchored POSIX-ERE ``rx`` with metacharacters escaped), and
  lists expand to a parenthesized ``or`` chain of conditions - parenthesized
  because the platform evaluates ``and``/``or`` strictly left-to-right with
  no precedence. Wildcard matching is case-sensitive, consistent with
  ``eq``. (#103)
- ``list()`` no longer returns every row when a filter cannot be applied.
  Shorthand filter kwargs were silently dropped whenever a manager supplied
  its own ``filter`` string, so ``client.vms.list(name=...)`` ignored the name
  and returned every non-snapshot VM - making the ordinary cleanup idiom
  ``for v in client.vms.list(name=missing): client.vms.delete(...)`` a
  destructive operation. A new ``combine_filters()`` helper merges both forms
  as ``(filter) and (built)``, and the 33 manager ``list()`` overrides that
  documented ``**kwargs`` as "additional filter arguments" without ever
  reading them now merge those kwargs into the filter they send. (#96)
- ``drive.tier = 2; drive.save()`` is no longer a silent no-op.
  ``ResourceObject._save()`` sends locally modified fields as a raw PUT that
  bypasses the typed ``update()``, so the ``tier`` -> ``preferred_tier``
  translation added in #81 was skipped and VergeOS accepted the raw ``tier``
  field with HTTP 200 and ignored it. A new
  ``ResourceManager._prepare_write_fields()`` hook applies alias translation
  on every write path, so attribute assignment and ``update()`` behave
  identically: ``tier`` -> ``preferred_tier`` (drives), ``network`` ->
  ``vnet`` (NICs), empty ``cloudinit_datasource`` -> ``"none"`` (VMs), and
  frequency/day validation plus ``max_tier`` coercion (snapshot profile
  periods). (#97)
- ``ResourceObject.refresh()`` now updates the object it is called on instead
  of returning a new one and leaving the receiver stale. The obvious wait loop
  (``while not vm.running: vm.refresh()``) converges as soon as the state
  changes rather than always running to its deadline. ``refresh()`` returns
  ``self``, so ``vm = vm.refresh()`` remains correct, and the 26 subclass
  overrides that existed only to narrow the return type were removed.
  ``SharedObject.refresh()`` gained the same in-place semantics;
  ``UpdateSource.refresh()``, which triggers an update check, is unchanged.
  (#98)
- Iterating a scoped collection no longer returns zero rows.
  ``iter_all()``/``__iter__`` pass ``limit``/``offset`` to ``list()``, and 19
  overrides consumed them as ``**kwargs`` filter arguments, producing filters
  such as ``(machine eq 55) and (limit eq 100 and offset eq 0)`` that matched
  nothing. Those overrides now declare ``limit``/``offset`` and send them as
  request parameters, so iteration works and pages server-side instead of
  re-fetching the full table. An AST-based guard test fails CI if a future
  ``list()`` override consumes ``**kwargs`` without declaring them. (#102)

- A ``fields`` string containing no field names - ``","``, ``"   "``, ``",,,"``
  - was passed through to the API, which answered with a single
  ``{"$count": N}`` row instead of the requested resources. Measured on
  VergeOS 26.1.8, a five-VM list collapsed to one meaningless row: the same
  silent-empty result #101 was filed for. Such values now mean "no projection
  requested". ``normalize_fields()`` and ``split_fields()`` also clean field
  names identically, so the string and sequence forms are interchangeable
  (``"$key,"`` and ``["$key", ""]`` now agree). A mapping, or a sequence
  containing a non-string, is rejected with ``TypeError`` rather than
  serialized into a plausible-looking but wrong projection. (#101)
- ``ResourceObject.update()`` and ``setdefault()`` bypassed dirty tracking,
  so ``obj.update({...}); obj.save()`` reported success while persisting
  nothing - the fields were changed locally and an empty ``PUT`` was sent.
  Both now route through the tracked ``__setitem__``, so a batch update
  behaves like a sequence of assignments. ``refresh()`` still bypasses
  tracking, as it loads server state rather than local edits. All 165
  resource classes inherit the fix. (#110)
- ``save()`` with nothing to save no longer issues an empty ``PUT``. An empty
  write is still subject to permissions, audit logging and update side
  effects, for a request the caller did not make; current state is returned
  instead. (#111)
- ``OidcApplicationManager.create()`` failed on any system without auth
  source key 0 and user key 0 - that is, any normal system. Both
  ``force_auth_source`` and ``map_user`` are required by the API but are
  resolved as row references, and the SDK coerced an unsupplied value from
  ``None`` to ``0``, which VergeOS rejects with HTTP 404 ``error setting
  field ... No such file or directory``. ``null`` is the accepted "not set"
  value and is now sent, so creating an application with only a name works.
  Explicitly supplied keys are unaffected. (#107)
- Every multi-value write parameter (``ssh_keys``, ``dns_servers``,
  ``ip_allow_list``, ``domain_list``, ``redirect_uri``, the NAS CIFS user and
  host lists, volume-sync ``include``/``exclude``) rejects a mapping, an
  unordered collection and non-string values instead of serializing them.
  Iterating a mapping yields its keys, so ``ssh_keys={"a": 1}`` was sent as
  ``'a'``; a ``set`` was joined in arbitrary order, and order is part of the
  value - the first entry of ``dnslist`` is the primary DNS server. (#101)
- ``WebhookManager.update(headers="")`` stored a lone blank line instead of
  clearing the header block, which ``headers={}`` already did correctly.
  Both forms now clear it. (#101)
- ``CertificateManager.get()`` and ``.list()`` silently ignored
  ``include_keys`` whenever an explicit ``fields`` projection was supplied, so
  the requested key material was missing from the result. The key fields are
  now appended to whatever projection was asked for, without duplicating
  entries, matching ``AuthSourceManager.get(include_settings=...)`` and
  ``OidcApplicationManager.get(include_secret=...)``. (#101)
- Six ``get()``/``list()`` methods still corrupted a ``fields`` string after
  the #101 sweep: ``auth_sources``, ``certificates``, ``cloudinit_files``
  (list and get), ``oidc_applications`` and ``webhooks`` build an *augmented*
  projection (adding ``settings``, ``client_secret`` and similar), so they
  aliased the parameter with ``list(fields)`` before joining and bypassed
  ``normalize_fields()``. ``list("$key,name")`` splits into characters exactly
  as ``",".join()`` does. A new ``split_fields()`` helper returns the list
  form, and the AST tripwire now follows locals that alias a parameter, which
  is how the original guard missed these. (#101)
- Filter values are no longer interpolated straight into a quoted literal.
  ``quote_value()`` exists so a caller-supplied value cannot be parsed as
  filter grammar, but **91 conditions across 40 modules never called it**,
  writing ``f"key ct '{key_contains}'"`` instead. A value containing an
  apostrophe broke out of the literal and the remainder was evaluated as
  grammar: measured on a live system,
  ``settings.list(key_contains="zzzz' or key ne 'zzzz")`` returned all 68
  rows instead of zero, and the same shape leaked whole tables from
  ``tasks.list_by_action()`` and ``task_events.list()``. The #100 brace
  effect reached these sites too - ``key_contains="clou{x}"`` silently
  matched ``clou`` - and a trailing backslash was rejected outright. This is
  not a privilege escalation: the injected condition runs with the caller's
  own permissions. The damage is wrong rows, and since the standard pattern
  is look-up-by-name then act on the returned key, a ``get_by_*`` resolving
  to the wrong row can lead to modifying or deleting the wrong object. All
  91 now route through ``quote_value()``; output is byte-identical for
  values with no reserved characters, so behaviour is unchanged otherwise.
  An AST tripwire fails CI if any filter condition interpolates a value
  directly inside ``'...'``. (#115)
- ``quote_value()`` now escapes ``{``, so a lookup by a name containing a
  brace no longer resolves to a different object. VergeOS reserves three
  characters inside a filter string literal - ``\\``, ``'`` and ``{`` - and
  only the first two were escaped. ``{`` opens a balanced, nesting-aware
  construct, so a *balanced* ``{...}`` was consumed silently and the query
  matched whatever the stripped string named: ``get(name="br{x}ace")``
  returned the unrelated row ``brace``, and because the standard pattern is
  look-up-by-name then act on the returned key, a caller could update or
  delete an object it never asked for. An unbalanced ``{`` was merely
  rejected with HTTP 422. The reserved set was re-measured by sweeping all 95
  printable ASCII characters against a live system and by round-tripping rows
  whose names contain each one; ``}`` is not reserved. The ``rx`` path is
  fixed by the same change - a brace there carries both the POSIX-ERE escape
  and the literal escape, and the previous single escape matched nothing. A
  tripwire test now pins the reserved set and fails if any ``{`` can reach the
  wire unescaped. (#100)
- ``Network.power_off(force=True)`` no longer sends an action the platform
  rejects. It emitted ``action="killpower"``, which is not in the vnet action
  list, so every forced power off of a network failed with ``ValidationError:
  value 'killpower' is not in list for field 'action'`` - forced power off was
  simply unavailable through the SDK. The valid value is ``kill``, the same
  value #42 applied to VMs; that fix was never carried across to networks, and
  the unit test asserted the broken string, so CI defended the bug. The
  ``_power_action()`` docstring advertised ``killpower`` as well. A new AST
  tripwire scans every resource module, so a third occurrence cannot ship.
  (#112)

Changed
^^^^^^^

- Filter kwargs whose values are all ``None`` (for example
  ``client.networks.list(name=None)``) now raise ``ValueError`` instead of
  producing an empty filter that matched every row. This matches the existing
  behaviour of ``get(name=None)``. Filter kwargs that are only partly ``None``
  still filter on the non-``None`` conditions. (#96)
- Invalid snapshot profile period fields now raise at ``save()`` as well as
  ``update()``, rather than being sent raw and silently ignored. (#97)
- An empty sequence passed as a filter value (``list(name=[])``) now raises
  ``ValueError`` instead of sending ``in ()``, which the platform rejected
  with an opaque 422. (#103)

Added
^^^^^

- ``Filter`` gained methods for the platform's native string operators:
  ``bw()`` (begins-with), ``ew()`` (ends-with), ``cs()`` (contains,
  case-sensitive), ``ct()`` (contains, case-insensitive) and ``rx()``
  (POSIX-ERE regex). (#103)

[1.2.7] - 2026-09-21
--------------------

Added
^^^^^

- ``UpdateSourceManager.run_preinstall_check()`` exposing the VergeOS 26.1
  table-level ``POST /update_actions/runpreinstallcheck`` action. The
  ``install`` action runs this check automatically; the method surfaces it
  directly as a convenience. (#68)

Fixed
^^^^^

- ``DriveManager.update()`` now translates ``tier`` to the API's
  ``preferred_tier`` field (as a string), matching ``create()`` and
  ``import_drive()``. Previously the raw ``tier`` field was sent, which
  VergeOS accepted with HTTP 200 and silently ignored, so a drive could be
  placed on a tier at creation but never re-tiered. ``tier=None`` is dropped;
  explicit ``preferred_tier`` passes through unchanged. (#81)
- ``VMDriveManager.create()`` now rejects ``size_gb`` for ``efidisk`` media.
  A caller-sized efidisk is created as a raw volume without the templated
  OVMF vars layout, so UEFI variables cannot persist and
  ``apply_universal_vars()`` fails with ``Operation not permitted``
  (verified on VergeOS 26.1.8). Omit the size so the platform templates the
  vars store. Documented that ``apply_universal_vars`` requires the
  path-form invocation - the generic ``?action=`` form is accepted with
  HTTP 200 but is a silent no-op. (#68)

[1.2.6] - 2026-09-21
--------------------

Fixed
^^^^^

- ``ResourceObject.save()`` now sends fields modified via attribute or item
  assignment (``vm.cpu_cores = 4; vm.save()``). Previously only keyword arguments
  were transmitted, so the ``setattr`` + ``save()`` pattern issued an empty ``PUT``
  and silently persisted nothing. Keyword arguments still take precedence over
  locally modified fields. (#80)
- System setting updates no longer send the read-only ``key`` field, which the
  API rejected with HTTP 422 (``field 'key' is readonly``). Only ``value`` is
  transmitted. (#86)
- Accept an empty ``cloudinit_datasource`` as a disable alias in VM creation,
  updates, and explicit ``save()`` arguments, consistent with
  ``set_cloudinit_datasource()``. Requests send VergeOS's valid ``"none"`` value;
  disabling delivery preserves files until callers explicitly delete them. (#82)

[1.2.5] - 2026-09-11
--------------------

Added
^^^^^

- Added ``vm_recipe_instances.simulate()`` to return recipe practice-run reports
  containing rendered cloud-init files, logs, and resolved answers. The helper
  recognizes VergeOS's HTTP 405 ``Simulation complete`` response without creating
  a persistent instance. ``create()`` also accepts ``simulate`` and ``verify`` flags.

Fixed
^^^^^

- Recognize native group membership references such as ``users/1`` and ``groups/3``,
  as well as prefixed references. Membership types and keys now resolve correctly,
  allowing removal helpers to find native memberships. Stored references are unchanged.
- Preserve the complete JSON error body in ``APIError.response_body`` and all
  subclasses, including the generic VergeOS ``response`` payload. Non-JSON error
  responses retain their raw text; error messages and status codes remain available.
- Fixed resource lookups and generated filters containing apostrophes or
  backslashes, including NAS paths and related-resource name resolution.
  Shared ``quote_value()`` now uses VergeOS backslash escaping instead of
  SQL quote doubling. Raw ``filter=`` expressions remain caller-controlled.

[1.2.4] - 2026-09-10
--------------------

Added
^^^^^

- Added ``Drive.ms_2023_kek_applied`` and
  ``Drive.apply_universal_vars()`` / ``DriveManager.apply_universal_vars()``
  for Microsoft 2023 Secure Boot key status and application on EFI disks.
- Added ``Tag`` and ``TagCategory`` log object-type mappings.

[1.2.3] - 2026-05-21
--------------------

Added
^^^^^

- Added ``session=`` and ``close_session=`` kwargs to ``VergeClient`` for
  caller-managed ``requests.Session`` support.

Changed
^^^^^^^

- ``VergeConnection`` now exposes its session as the public ``session`` field.
  The previous private ``_session`` attribute has been removed.
- Caller-supplied sessions are not closed by default on disconnect, and
  VergeOS auth/content headers are restored to their pre-connect values.
- Retry and ``verify_ssl`` connection options are ignored with a warning when
  a caller-supplied session is used; configure those behaviors on the supplied
  session instead.
- Caller-supplied sessions must not be shared by multiple active
  ``VergeClient`` instances because authentication is stored in session headers
  while connected.
- ``close_session=False`` now requires a caller-supplied session to avoid
  leaking SDK-created connection pools.

[1.0.0] - 2026-02-01
--------------------

First stable release with full API coverage for VergeOS 26.0+.

Added
^^^^^

**Core Automation (Phase 1)**

- **VM Import/Export System**

  - ``VmImportManager`` - Import VMs from VMDK, QCOW2, OVA, OVF formats
  - ``VmImportLogManager`` - Track import progress and errors
  - ``VolumeVmExportManager`` - Export VMs to NAS volumes for backup
  - ``VolumeVmExportStatManager`` - Monitor export progress

- **Recipe/Provisioning System**

  - ``VmRecipeManager`` - VM recipe templates
  - ``VmRecipeInstanceManager`` - Deployed VM instances from recipes
  - ``VmRecipeLogManager`` - Recipe deployment logs
  - ``TenantRecipeManager`` - Tenant recipe templates
  - ``TenantRecipeInstanceManager`` - Deployed tenant instances
  - ``TenantRecipeLogManager`` - Tenant recipe deployment logs
  - ``RecipeQuestionManager`` - Recipe configuration questions
  - ``RecipeSectionManager`` - Recipe form sections

- **Task Scheduling System**

  - ``TaskScheduleManager`` - Cron-style schedule definitions
  - ``TaskScheduleTriggerManager`` - Schedule triggers for tasks
  - ``TaskEventManager`` - Event definitions for task triggers
  - ``TaskScriptManager`` - Task script management
  - Enhanced ``TaskManager`` with full CRUD operations

- **Catalog Management**

  - ``CatalogRepositoryManager`` - Repository sources (local, remote, git)
  - ``CatalogManager`` - Catalog entries
  - ``CatalogRepositoryStatusManager`` - Repository sync status
  - ``CatalogLogManager`` - Catalog activity logs

**Enterprise Networking (Phase 2)**

- **Network Routing Protocols**

  - ``NetworkRoutingManager`` - Entry point via ``network.routing``
  - ``BgpRouterManager`` - BGP router configuration
  - ``BgpInterfaceManager`` - BGP interface configuration
  - ``BgpRouteMapManager`` - BGP route maps
  - ``BgpIpCommandManager`` - BGP prefix-lists and AS-path access-lists
  - ``OspfCommandManager`` - OSPF protocol commands
  - ``EigrpRouterManager`` - EIGRP router configuration

- **Tenant Proxy**

  - ``VnetProxyManager`` - Reverse proxy service configuration
  - ``VnetProxyTenantManager`` - Tenant FQDN mappings

**Infrastructure Monitoring (Phase 3)**

- **Machine Stats & Monitoring**

  - ``MachineStatsManager`` - Real-time VM/node performance metrics
  - ``MachineStatsHistory`` - Historical metrics (short-term and long-term)
  - ``MachineStatusManager`` - VM/node operational status
  - ``MachineLogManager`` - VM/node-specific logs
  - ``MachineDeviceManager`` - GPU, TPM, USB device management

- **GPU/vGPU Management**

  - ``NvidiaVgpuProfileManager`` - Available vGPU profiles
  - ``NodeVgpuDeviceManager`` - Physical vGPU devices
  - ``NodeVgpuProfileManager`` - Node-specific vGPU profiles
  - ``NodeGpuManager`` - Physical GPU configuration
  - ``NodeGpuStatsManager`` - GPU utilization metrics with history
  - ``NodeGpuInstanceManager`` - GPU instances assigned to VMs
  - ``NodeHostGpuDeviceManager`` - Host GPU devices for passthrough

- **Cluster Tier Management**

  - ``ClusterTierManager`` - Storage tier management
  - ``ClusterTierStatus`` - Tier health status
  - ``ClusterTierStats`` - Tier I/O performance metrics

- **Tenant Stats & Monitoring**

  - ``TenantStatsManager`` - Tenant resource utilization
  - ``TenantStatsHistory`` - Historical tenant metrics
  - ``TenantDashboardManager`` - Aggregated tenant overview
  - ``TenantLogManager`` - Tenant activity logging

- **Billing System**

  - ``BillingManager`` - Resource usage tracking and billing reports
  - Time-based filtering with datetime or epoch timestamps
  - Summary statistics with averages and peak values

**Existing Resource Enhancements (Phase 4)**

- **VM Enhancements**

  - ``migrate()`` - Live migrate VM to another node
  - ``hibernate()`` - Hibernate VM to disk
  - ``change_cd()`` - Change CD/DVD media
  - ``restore()`` - Restore from snapshot
  - ``hotplug_drive()`` - Hot-add drive to running VM
  - ``hotplug_nic()`` - Hot-add NIC to running VM
  - ``tag()`` / ``untag()`` - Tag management
  - ``favorite()`` / ``unfavorite()`` - VM favorites

- **Network Enhancements**

  - ``NetworkMonitorStatsManager`` - Network performance monitoring
  - ``NetworkDashboardManager`` - Network topology discovery
  - ``IPSecActiveConnectionManager`` - IPSec connection tracking
  - ``WireGuardPeerStatusManager`` - WireGuard peer status

- **Site Sync Enhancements**

  - ``SiteSyncQueueManager`` - Sync queue management
  - ``SiteSyncRemoteSnapManager`` - Remote snapshot visibility
  - ``SiteSyncIncomingVerifiedManager`` - Verified incoming syncs
  - ``SiteSyncStatsManager`` - Sync performance metrics

**Authentication & Security (Phase 5)**

- **Authentication Sources**

  - ``AuthSourceManager`` - External auth providers (OAuth2, OIDC, Azure AD, Okta)
  - ``AuthSourceStateManager`` - Auth source connection state

- **OIDC Applications**

  - ``OidcApplicationManager`` - Use VergeOS as identity provider
  - ``OidcApplicationUserManager`` - User ACLs for OIDC apps
  - ``OidcApplicationGroupManager`` - Group ACLs for OIDC apps
  - ``OidcApplicationLogManager`` - OIDC application logs

- **Update Management**

  - ``UpdateSettingsManager`` - Update configuration
  - ``UpdateSourceManager`` - Update source management
  - ``UpdateBranchManager`` - Available update branches
  - ``UpdatePackageManager`` - Available packages
  - ``UpdateDashboardManager`` - Update status dashboard
  - ``UpdateLogManager`` - Update history

**Documentation (Phase 6)**

- Sphinx documentation with autodoc API reference
- Tutorials for VM import/export, recipes, task scheduling, routing, GPU passthrough
- Migration guide from direct API calls
- Troubleshooting guide
- 25 example scripts covering major use cases

Changed
^^^^^^^

- Minimum VergeOS version requirement: 26.0+
- Test coverage increased to 83% (3,686+ tests)
- All resource managers now export type-safe model classes
- Improved error messages with actionable context

Fixed
^^^^^

- Consistent retry behavior across all HTTP methods
- Proper handling of 40-character hex string keys in recipes and catalogs
- Scoped managers correctly inherit parent context

[0.1.1] - 2026-01-29
--------------------

Added
^^^^^

- Configurable retry strategy for HTTP requests

  - ``retry_total`` - Number of retry attempts (default: 3)
  - ``retry_backoff_factor`` - Exponential backoff multiplier (default: 1)
  - ``retry_status_codes`` - HTTP codes to retry (default: 429, 500, 502, 503, 504)

- System enhancements for diagnostics, certificates, and settings
- Unit tests for remaining resource managers

[0.1.0] - 2026-01-15
--------------------

Initial release.

Added
^^^^^

- Core client with username/password and token authentication
- Virtual machine management (CRUD, power operations, snapshots)
- Network management (CRUD, firewall rules, DNS)
- Tenant management
- NAS/storage management
- User and group management
- Task monitoring and waiting
- OData filter builder
- Automatic retry with exponential backoff
- Comprehensive exception hierarchy
- Full type annotations
