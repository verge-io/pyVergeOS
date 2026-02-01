Tutorials
=========

This section provides step-by-step tutorials for common workflows with pyvergeos.

.. contents:: Tutorials
   :local:
   :depth: 2

VM Import and Export
--------------------

pyvergeos supports importing VMs from various formats and exporting VMs to NAS volumes
for backup and migration workflows.

Importing VMs from Files
^^^^^^^^^^^^^^^^^^^^^^^^

Import VMs from VMDK, QCOW2, OVA, or OVF files:

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # List existing import jobs
       imports = client.vm_imports.list()
       for imp in imports:
           print(f"{imp.name}: {imp.status}")

       # Import from a NAS volume
       # First, set up a remote volume pointing to your NFS/CIFS share
       volume = client.nas_volumes.get(name="vmware-exports")

       # Create an import job
       import_job = client.vm_imports.create(
           name="Import from VMware",
           volume=volume.key,
           preserve_mac=True,  # Keep original MAC addresses
       )

       # Monitor import progress
       for log in import_job.logs.list():
           print(f"[{log.level}] {log.text}")

       # Wait for completion
       import_job = import_job.wait(timeout=3600)
       print(f"Import status: {import_job.status}")

Exporting VMs to NAS
^^^^^^^^^^^^^^^^^^^^

Export VMs to a NAS volume for backup or migration:

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # First, enable export on the VM
       vm = client.vms.get(name="web-server")
       vm.update(allow_export=True)

       # Create a VM export volume
       nas = client.nas_services.get(name="NAS1")
       export_volume = nas.volumes.create(
           name="vm-exports",
           volume_type="vmexport",  # Special export volume type
       )

       # Create an export job
       export = client.volume_vm_exports.create(
           name="Weekly Backup Export",
           volume=export_volume.key,
       )

       # Run the export
       result = export.action("export")

       # Monitor progress via stats
       stats = export.stats.get()
       print(f"Progress: {stats.percent_complete}%")

Recipe-Based Provisioning
-------------------------

Recipes provide templates for deploying standardized VMs and tenants.

Deploying a VM from a Recipe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient
   from pyvergeos.exceptions import NotFoundError

   with VergeClient.from_env() as client:
       # List available recipes
       recipes = client.vm_recipes.list(downloaded=True)
       for recipe in recipes:
           print(f"{recipe.name} v{recipe.version}")

       # Get a specific recipe
       recipe = client.vm_recipes.get(name="Ubuntu Server 22.04")

       # View configuration questions
       recipe_ref = f"vm_recipes/{recipe.key}"
       questions = client.recipe_questions.list(
           recipe_ref=recipe_ref,
           enabled=True,
       )

       for q in questions:
           print(f"{q.name}: {q.question_type} ({q.display})")

       # Prepare answers for deployment
       answers = {
           "YB_CPU_CORES": 2,
           "YB_RAM": 4096,
           "YB_HOSTNAME": "web-server-01",
           "YB_IP_ADDR_TYPE": "dhcp",
           "YB_USER": "ubuntu",
           "YB_PASSWORD": "secure-password",
       }

       # Deploy the recipe
       instance = recipe.deploy(
           name="web-server-01",
           answers=answers,
           auto_update=False,
       )

       print(f"Created VM: {instance.vm_key}")

Managing Recipe Instances
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   with VergeClient.from_env() as client:
       # List all recipe instances
       instances = client.vm_recipe_instances.list()
       for inst in instances:
           print(f"{inst.name}: Recipe {inst.recipe_name} v{inst.version}")

       # Get instances for a specific recipe
       recipe = client.vm_recipes.get(name="Ubuntu Server 22.04")
       for inst in recipe.instances.list():
           print(f"  - {inst.name}")

       # View recipe deployment logs
       for log in recipe.logs.list(limit=10):
           print(f"[{log.level}] {log.text}")

Task Scheduling and Automation
------------------------------

The Task Engine enables automated operations on schedules or events.

Creating Scheduled Tasks
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # Get a VM to manage
       vm = client.vms.get(name="dev-server")

       # Create a power-off task
       task = client.tasks.create(
           name="Power Off Dev Server",
           owner=vm.key,
           action="poweroff",
           description="Automatically power off at end of business",
           enabled=True,
       )

       # Create a Friday 6 PM schedule
       # Time is seconds from midnight: 18:00 = 64800
       schedule = client.task_schedules.create(
           name="Friday EOB",
           description="Every Friday at 6:00 PM",
           repeat_every="week",
           repeat_iteration=1,
           start_time_of_day=64800,
           friday=True,
           monday=False,
           tuesday=False,
           wednesday=False,
           thursday=False,
           saturday=False,
           sunday=False,
           enabled=True,
       )

       # Link task to schedule
       trigger = client.task_schedule_triggers.create(
           task=task.key,
           schedule=schedule.key,
       )

       print(f"Task '{task.name}' will run {schedule.name}")

Working with Task Triggers
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   with VergeClient.from_env() as client:
       # View task triggers
       task = client.tasks.get(name="Power Off Dev Server")

       # Schedule triggers
       for trigger in task.triggers.list():
           print(f"Schedule: {trigger.schedule_display}")

       # Event triggers
       for event in task.events.list():
           print(f"Event: {event.event_name_display}")

       # Execute task manually
       task.execute()
       task.wait(timeout=60)

       # Enable/disable task
       task.disable()
       task.enable()

Routing Protocol Configuration
------------------------------

Configure BGP, OSPF, and EIGRP for enterprise networking.

BGP Configuration
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # Get the network
       network = client.networks.get(name="WAN")

       # Access routing manager
       routing = network.routing

       # Create a BGP router
       bgp_router = routing.bgp_routers.create(
           name="edge-bgp",
           asn=65001,
           router_id="10.0.0.1",
           enabled=True,
       )

       # Add BGP commands (neighbor configuration)
       bgp_router.commands.create(
           command="neighbor 10.0.0.2 remote-as 65002",
       )
       bgp_router.commands.create(
           command="neighbor 10.0.0.2 description ISP-Upstream",
       )

       # Create a route map
       route_map = routing.bgp_route_maps.create(
           name="OUTBOUND-FILTER",
           tag="outbound",
           sequence=10,
           permit=True,
       )

       # Create IP prefix list
       routing.bgp_ip_commands.create(
           command="ip prefix-list ALLOWED permit 10.0.0.0/8 le 24",
       )

       # Apply routing changes
       network.apply_rules()

OSPF Configuration
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   with VergeClient.from_env() as client:
       network = client.networks.get(name="Internal")
       routing = network.routing

       # Create OSPF commands
       routing.ospf_commands.create(
           command="router ospf 1",
       )
       routing.ospf_commands.create(
           command="network 10.0.0.0/24 area 0",
       )
       routing.ospf_commands.create(
           command="passive-interface default",
       )

       network.apply_rules()

GPU Passthrough
---------------

Configure GPU passthrough for AI/ML and visualization workloads.

Setting Up GPU Passthrough
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # Find the node with GPU
       node = client.nodes.get(name="gpu-node-01")

       # List available PCI devices
       for pci in node.pci_devices.list():
           if "NVIDIA" in pci.name or "VGA" in pci.name:
               print(f"GPU: {pci.name} at slot {pci.slot}")

       # Create a resource group for the GPU
       resource_group = client.resource_groups.create_pci(
           name="RTX-4090-Passthrough",
           description="NVIDIA RTX 4090 for ML workloads",
           device_class="gpu",
           enabled=True,
       )

       # Create a rule to select the GPU by PCI slot
       resource_group.rules.create(
           name="GPU at 01:00.0",
           filter_expression="slot eq '01:00.0'",
           node=node.key,
           enabled=True,
       )

       # Attach GPU to VM (VM should be powered off)
       vm = client.vms.get(name="ml-workstation")
       device = vm.devices.create_pci(
           resource_group=resource_group.key,
           enabled=True,
           optional=False,  # VM requires this device
       )

       print(f"Attached {device.name} to {vm.name}")

Monitoring GPU Usage
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   with VergeClient.from_env() as client:
       # Get GPU stats for a node
       node = client.nodes.get(name="gpu-node-01")

       for gpu in node.gpus.list():
           stats = gpu.stats.get()
           print(f"{gpu.name}:")
           print(f"  Utilization: {stats.utilization}%")
           print(f"  Memory Used: {stats.memory_used}/{stats.memory_total} MB")
           print(f"  Temperature: {stats.temperature}C")

       # Historical GPU stats
       history = gpu.stats.history_short()
       for point in history:
           print(f"{point.timestamp}: {point.utilization}%")

Multi-Tenant Monitoring
-----------------------

Monitor resource usage across tenants for capacity planning and billing.

Tenant Dashboard
^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # Get tenant dashboard overview
       dashboard = client.tenant_dashboard.get()

       print(f"Total Tenants: {dashboard.tenant_count}")
       print(f"Running: {dashboard.running_count}")
       print(f"Stopped: {dashboard.stopped_count}")

       # Top resource consumers
       print("\nTop RAM Consumers:")
       for tenant in dashboard.top_ram_consumers[:5]:
           print(f"  {tenant['name']}: {tenant['ram_used']} MB")

       print("\nTop Storage Consumers:")
       for tenant in dashboard.top_storage_consumers[:5]:
           print(f"  {tenant['name']}: {tenant['storage_used']} GB")

Tenant-Specific Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   with VergeClient.from_env() as client:
       tenant = client.tenants.get(name="customer-a")

       # Current stats
       stats = tenant.stats.get()
       print(f"Tenant: {tenant.name}")
       print(f"  RAM Used: {stats.ram_used} MB")
       print(f"  CPU Cores: {stats.cpu_cores}")

       # Historical usage (for billing/trending)
       history = tenant.stats.history_long(limit=30)
       for point in history:
           print(f"{point.timestamp}: RAM={point.ram_used}MB")

       # Tenant logs
       for log in tenant.logs.list(level="warning", limit=10):
           print(f"[{log.level}] {log.text}")

       # Error logs only
       errors = tenant.logs.list_errors(limit=5)
       for err in errors:
           print(f"ERROR: {err.text}")

Billing Reports
^^^^^^^^^^^^^^^

.. code-block:: python

   from datetime import datetime, timedelta

   with VergeClient.from_env() as client:
       # Get billing records for the last month
       end_date = datetime.now()
       start_date = end_date - timedelta(days=30)

       records = client.billing.list(
           start_time=start_date,
           end_time=end_date,
       )

       for record in records:
           print(f"Date: {record.timestamp}")
           print(f"  CPU: {record.cpu_used}")
           print(f"  RAM: {record.ram_used} MB")
           print(f"  Storage Tier 0: {record.tier0_used} GB")

       # Generate a billing report
       result = client.billing.generate()
       print(f"Report generated: {result}")

       # Get summary statistics
       summary = client.billing.get_summary(
           start_time=start_date,
           end_time=end_date,
       )
       print(f"Average RAM: {summary.avg_ram_used} MB")
       print(f"Peak RAM: {summary.peak_ram_used} MB")

Site Sync and DR
----------------

Configure disaster recovery with site synchronization.

Setting Up Site Sync
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient.from_env() as client:
       # List outgoing sync configurations
       syncs = client.site_syncs.outgoing.list()
       for sync in syncs:
           print(f"{sync.name}: {sync.status}")

       # Get sync stats
       sync = client.site_syncs.outgoing.get(name="DR-Site")
       stats = sync.stats.get()
       print(f"Last sync: {stats.last_sync_time}")
       print(f"Data synced: {stats.bytes_synced} bytes")

       # View sync queue
       for item in sync.queue.list():
           print(f"Queued: {item.name} ({item.size} bytes)")

       # View remote snapshots
       for snap in sync.remote_snaps.list():
           print(f"Remote: {snap.name} at {snap.timestamp}")

       # Monitor sync history
       history = sync.stats.history_short()
       for point in history:
           print(f"{point.timestamp}: {point.throughput} MB/s")
