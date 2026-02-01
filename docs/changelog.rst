Changelog
=========

All notable changes to pyvergeos will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

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
