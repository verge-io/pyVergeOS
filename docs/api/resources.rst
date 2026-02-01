Resources
=========

pyvergeos provides resource managers for all VergeOS API endpoints.
Each resource follows a consistent CRUD pattern with additional domain-specific methods.

.. contents:: Resource Categories
   :local:
   :depth: 2

Virtual Machines
----------------

Core VM Management
^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.vms
   :members:
   :undoc-members:
   :show-inheritance:

VM Drives
^^^^^^^^^

.. automodule:: pyvergeos.resources.drives
   :members:
   :undoc-members:
   :show-inheritance:

VM NICs
^^^^^^^

.. automodule:: pyvergeos.resources.nics
   :members:
   :undoc-members:
   :show-inheritance:

VM Snapshots
^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.snapshots
   :members:
   :undoc-members:
   :show-inheritance:

VM Import/Export
^^^^^^^^^^^^^^^^

Import VMs from various formats (VMDK, QCOW2, OVA, OVF) and export VMs to NAS volumes.

.. automodule:: pyvergeos.resources.vm_imports
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: pyvergeos.resources.volume_vm_exports
   :members:
   :undoc-members:
   :show-inheritance:

Machine Stats & Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^

Real-time and historical performance metrics for VMs and nodes.

.. automodule:: pyvergeos.resources.machine_stats
   :members:
   :undoc-members:
   :show-inheritance:

Networks
--------

Core Network Management
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.networks
   :members:
   :undoc-members:
   :show-inheritance:

Firewall Rules
^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.rules
   :members:
   :undoc-members:
   :show-inheritance:

DNS
^^^

.. automodule:: pyvergeos.resources.dns
   :members:
   :undoc-members:
   :show-inheritance:

IP Aliases
^^^^^^^^^^

.. automodule:: pyvergeos.resources.aliases
   :members:
   :undoc-members:
   :show-inheritance:

DHCP Hosts
^^^^^^^^^^

.. automodule:: pyvergeos.resources.hosts
   :members:
   :undoc-members:
   :show-inheritance:

Network Statistics
^^^^^^^^^^^^^^^^^^

Network performance monitoring and topology discovery.

.. automodule:: pyvergeos.resources.network_stats
   :members:
   :undoc-members:
   :show-inheritance:

Routing Protocols
^^^^^^^^^^^^^^^^^

BGP, OSPF, and EIGRP configuration for enterprise deployments.

.. automodule:: pyvergeos.resources.routing
   :members:
   :undoc-members:
   :show-inheritance:

IPSec VPN
^^^^^^^^^

.. automodule:: pyvergeos.resources.ipsec
   :members:
   :undoc-members:
   :show-inheritance:

WireGuard VPN
^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.wireguard
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Proxy
^^^^^^^^^^^^

Reverse proxy for multi-tenant FQDN-based access.

.. automodule:: pyvergeos.resources.vnet_proxy
   :members:
   :undoc-members:
   :show-inheritance:

Tenants
-------

Tenant Management
^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_manager
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Stats & Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^

Resource utilization and activity logging for tenants.

.. automodule:: pyvergeos.resources.tenant_stats
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Storage
^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_storage
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Network Blocks
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_network_blocks
   :members:
   :undoc-members:
   :show-inheritance:

Tenant External IPs
^^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_external_ips
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Snapshots
^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_snapshots
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Layer 2 Networks
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_layer2
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Nodes
^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.tenant_nodes
   :members:
   :undoc-members:
   :show-inheritance:

Storage
-------

NAS Services
^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_services
   :members:
   :undoc-members:
   :show-inheritance:

NAS Volumes
^^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_volumes
   :members:
   :undoc-members:
   :show-inheritance:

NAS Volume Browser
^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_volume_browser
   :members:
   :undoc-members:
   :show-inheritance:

NAS Volume Syncs
^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_volume_syncs
   :members:
   :undoc-members:
   :show-inheritance:

CIFS Shares
^^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_cifs
   :members:
   :undoc-members:
   :show-inheritance:

NFS Shares
^^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_nfs
   :members:
   :undoc-members:
   :show-inheritance:

NAS Users
^^^^^^^^^

.. automodule:: pyvergeos.resources.nas_users
   :members:
   :undoc-members:
   :show-inheritance:

Storage Tiers
^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.storage_tiers
   :members:
   :undoc-members:
   :show-inheritance:

Recipes & Catalogs
------------------

VM Recipes
^^^^^^^^^^

Automated VM provisioning templates.

.. automodule:: pyvergeos.resources.vm_recipes
   :members:
   :undoc-members:
   :show-inheritance:

Tenant Recipes
^^^^^^^^^^^^^^

Automated tenant provisioning templates.

.. automodule:: pyvergeos.resources.tenant_recipes
   :members:
   :undoc-members:
   :show-inheritance:

Recipe Components
^^^^^^^^^^^^^^^^^

Questions and sections used in recipes.

.. automodule:: pyvergeos.resources.recipe_common
   :members:
   :undoc-members:
   :show-inheritance:

Catalogs
^^^^^^^^

Recipe catalog and repository management.

.. automodule:: pyvergeos.resources.catalogs
   :members:
   :undoc-members:
   :show-inheritance:

Task Scheduling
---------------

Tasks
^^^^^

Task management and waiting.

.. automodule:: pyvergeos.resources.tasks
   :members:
   :undoc-members:
   :show-inheritance:

Task Schedules
^^^^^^^^^^^^^^

Cron-style schedule definitions.

.. automodule:: pyvergeos.resources.task_schedules
   :members:
   :undoc-members:
   :show-inheritance:

Task Schedule Triggers
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.task_schedule_triggers
   :members:
   :undoc-members:
   :show-inheritance:

Task Events
^^^^^^^^^^^

Event definitions for task triggers.

.. automodule:: pyvergeos.resources.task_events
   :members:
   :undoc-members:
   :show-inheritance:

Task Scripts
^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.task_scripts
   :members:
   :undoc-members:
   :show-inheritance:

Users and Groups
----------------

Users
^^^^^

.. automodule:: pyvergeos.resources.users
   :members:
   :undoc-members:
   :show-inheritance:

Groups
^^^^^^

.. automodule:: pyvergeos.resources.groups
   :members:
   :undoc-members:
   :show-inheritance:

API Keys
^^^^^^^^

.. automodule:: pyvergeos.resources.api_keys
   :members:
   :undoc-members:
   :show-inheritance:

Permissions
^^^^^^^^^^^

.. automodule:: pyvergeos.resources.permissions
   :members:
   :undoc-members:
   :show-inheritance:

Authentication & Security
-------------------------

Authentication Sources
^^^^^^^^^^^^^^^^^^^^^^

External identity providers (OAuth2, OIDC, Azure AD, Okta).

.. automodule:: pyvergeos.resources.auth_sources
   :members:
   :undoc-members:
   :show-inheritance:

OIDC Applications
^^^^^^^^^^^^^^^^^

Use VergeOS as an identity provider.

.. automodule:: pyvergeos.resources.oidc_applications
   :members:
   :undoc-members:
   :show-inheritance:

Certificates
^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.certificates
   :members:
   :undoc-members:
   :show-inheritance:

System
------

System Management
^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.system
   :members:
   :undoc-members:
   :show-inheritance:

Clusters
^^^^^^^^

.. automodule:: pyvergeos.resources.clusters
   :members:
   :undoc-members:
   :show-inheritance:

Cluster Tiers
^^^^^^^^^^^^^

Storage tier health and performance monitoring.

.. automodule:: pyvergeos.resources.cluster_tiers
   :members:
   :undoc-members:
   :show-inheritance:

Nodes
^^^^^

.. automodule:: pyvergeos.resources.nodes
   :members:
   :undoc-members:
   :show-inheritance:

GPU/vGPU Management
^^^^^^^^^^^^^^^^^^^

GPU passthrough and vGPU configuration.

.. automodule:: pyvergeos.resources.gpu
   :members:
   :undoc-members:
   :show-inheritance:

Devices
^^^^^^^

.. automodule:: pyvergeos.resources.devices
   :members:
   :undoc-members:
   :show-inheritance:

Logs
^^^^

.. automodule:: pyvergeos.resources.logs
   :members:
   :undoc-members:
   :show-inheritance:

Alarms
^^^^^^

.. automodule:: pyvergeos.resources.alarms
   :members:
   :undoc-members:
   :show-inheritance:

Update Management
^^^^^^^^^^^^^^^^^

System update configuration and application.

.. automodule:: pyvergeos.resources.updates
   :members:
   :undoc-members:
   :show-inheritance:

Billing
^^^^^^^

Resource usage tracking and billing reports.

.. automodule:: pyvergeos.resources.billing
   :members:
   :undoc-members:
   :show-inheritance:

Backup & DR
-----------

Cloud Snapshots
^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.cloud_snapshots
   :members:
   :undoc-members:
   :show-inheritance:

Snapshot Profiles
^^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.snapshot_profiles
   :members:
   :undoc-members:
   :show-inheritance:

Sites
^^^^^

.. automodule:: pyvergeos.resources.sites
   :members:
   :undoc-members:
   :show-inheritance:

Site Syncs
^^^^^^^^^^

DR synchronization management.

.. automodule:: pyvergeos.resources.site_syncs
   :members:
   :undoc-members:
   :show-inheritance:

Organization
------------

Tags
^^^^

.. automodule:: pyvergeos.resources.tags
   :members:
   :undoc-members:
   :show-inheritance:

Resource Groups
^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.resource_groups
   :members:
   :undoc-members:
   :show-inheritance:

Shared Objects
^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.shared_objects
   :members:
   :undoc-members:
   :show-inheritance:

Cloud-Init Files
^^^^^^^^^^^^^^^^

.. automodule:: pyvergeos.resources.cloudinit_files
   :members:
   :undoc-members:
   :show-inheritance:

Files
^^^^^

.. automodule:: pyvergeos.resources.files
   :members:
   :undoc-members:
   :show-inheritance:

Webhooks
^^^^^^^^

.. automodule:: pyvergeos.resources.webhooks
   :members:
   :undoc-members:
   :show-inheritance:

Base Classes
------------

.. automodule:: pyvergeos.resources.base
   :members:
   :undoc-members:
   :show-inheritance:
