Changelog
=========

All notable changes to pyvergeos will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

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
