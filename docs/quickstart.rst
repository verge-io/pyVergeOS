Quick Start
===========

This guide will help you get started with pyvergeos in minutes.

Installation
------------

Install pyvergeos using pip:

.. code-block:: bash

   pip install pyvergeos

Or with uv:

.. code-block:: bash

   uv add pyvergeos

Basic Usage
-----------

Connect to VergeOS
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyvergeos import VergeClient

   # Connect with username/password
   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       verify_ssl=False  # For self-signed certificates
   )

   # Always disconnect when done
   client.disconnect()

Using Context Manager (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The context manager automatically handles connection cleanup:

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient(host="192.168.1.100", username="admin", password="secret") as client:
       vms = client.vms.list()
       # Connection automatically closed when exiting the block

Working with Virtual Machines
-----------------------------

List VMs
^^^^^^^^

.. code-block:: python

   # List all VMs
   vms = client.vms.list()
   for vm in vms:
       print(f"{vm.name}: {vm.ram}MB RAM, {vm.cpu_cores} cores")

   # Filter VMs
   linux_vms = client.vms.list(os_family="linux")
   running_vms = client.vms.list(status="running")

Get a Specific VM
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # By ID (key)
   vm = client.vms.get(123)

   # By name
   vm = client.vms.get(name="web-server")

Create a VM
^^^^^^^^^^^

.. code-block:: python

   vm = client.vms.create(
       name="my-vm",
       ram=2048,
       cpu_cores=2,
       os_family="linux"
   )

Power Operations
^^^^^^^^^^^^^^^^

.. code-block:: python

   vm.power_on()
   vm.power_off()
   vm.reset()
   vm.guest_reboot()  # Graceful reboot via guest agent

Snapshots
^^^^^^^^^

.. code-block:: python

   # Create a snapshot
   vm.snapshot(name="before-upgrade", quiesce=True)

   # List snapshots
   snapshots = vm.snapshots.list()

Working with Networks
---------------------

.. code-block:: python

   # List networks
   networks = client.networks.list()

   # Create a network
   network = client.networks.create(
       name="app-network",
       network_address="10.10.1.0/24",
       ip_address="10.10.1.1",
       dhcp_enabled=True
   )

   # Power on the network
   network.power_on()

   # Apply firewall rules
   network.apply_rules()

Working with Tenants
--------------------

.. code-block:: python

   # List tenants
   tenants = client.tenants.list()

   # Create a tenant
   tenant = client.tenants.create(name="customer-a")

   # Power on
   tenant.power_on()

Next Steps
----------

- :doc:`authentication` - Learn about authentication options
- :doc:`filtering` - Advanced filtering and pagination
- :doc:`error_handling` - Handle errors gracefully
- :doc:`api/resources` - Full API reference
