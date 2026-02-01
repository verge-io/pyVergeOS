Migration Guide
===============

This guide helps you migrate from direct VergeOS API calls to using the pyvergeos SDK.

.. contents:: Contents
   :local:
   :depth: 2

Why Migrate to pyvergeos?
-------------------------

The pyvergeos SDK provides several advantages over direct API calls:

- **Type Safety**: Full type annotations for IDE autocompletion and static analysis
- **Error Handling**: Custom exception hierarchy with clear, actionable error messages
- **Authentication**: Automatic session management and token refresh
- **Retries**: Built-in retry logic with exponential backoff for transient failures
- **Consistency**: Uniform CRUD patterns across all 68+ resource managers
- **Pagination**: Automatic pagination with ``iter_all()`` for large result sets

Before and After
----------------

Authentication
^^^^^^^^^^^^^^

**Direct API (requests):**

.. code-block:: python

   import requests

   session = requests.Session()
   response = session.post(
       "https://192.168.1.100/api/v4/auth",
       json={"username": "admin", "password": "secret"},
       verify=False
   )
   token = response.json()["token"]
   session.headers.update({"Authorization": f"Bearer {token}"})

**With pyvergeos:**

.. code-block:: python

   from pyvergeos import VergeClient

   # Direct credentials
   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       verify_ssl=False
   )

   # Or from environment variables
   client = VergeClient.from_env()

   # Or with context manager (recommended)
   with VergeClient.from_env() as client:
       # Connection automatically closed

Listing Resources
^^^^^^^^^^^^^^^^^

**Direct API:**

.. code-block:: python

   response = session.get(
       "https://192.168.1.100/api/v4/vms",
       params={"filter": "status eq 'running'", "limit": 100}
   )
   vms = response.json()["data"]

**With pyvergeos:**

.. code-block:: python

   # Simple list
   vms = client.vms.list(status="running")

   # With OData filter
   vms = client.vms.list(filter="ram gt 4096 and os_family eq 'linux'")

   # Iterate all (automatic pagination)
   for vm in client.vms.iter_all():
       print(vm.name)

Getting a Resource
^^^^^^^^^^^^^^^^^^

**Direct API:**

.. code-block:: python

   response = session.get("https://192.168.1.100/api/v4/vms/123")
   if response.status_code == 404:
       raise Exception("VM not found")
   vm = response.json()

**With pyvergeos:**

.. code-block:: python

   from pyvergeos.exceptions import NotFoundError

   # By ID
   vm = client.vms.get(123)

   # By name
   vm = client.vms.get(name="web-server")

   # With error handling
   try:
       vm = client.vms.get(name="nonexistent")
   except NotFoundError:
       print("VM not found")

Creating Resources
^^^^^^^^^^^^^^^^^^

**Direct API:**

.. code-block:: python

   response = session.post(
       "https://192.168.1.100/api/v4/vms",
       json={
           "name": "test-vm",
           "ram": 2048,
           "cpu_cores": 2,
           "os_family": "linux"
       }
   )
   if response.status_code not in (200, 201):
       raise Exception(response.json().get("error", "Unknown error"))
   vm = response.json()

**With pyvergeos:**

.. code-block:: python

   vm = client.vms.create(
       name="test-vm",
       ram=2048,
       cpu_cores=2,
       os_family="linux"
   )
   print(f"Created VM: {vm.key}")

Performing Actions
^^^^^^^^^^^^^^^^^^

**Direct API:**

.. code-block:: python

   # Power on
   response = session.post(
       "https://192.168.1.100/api/v4/vms/123/actions",
       json={"action": "poweron"}
   )

   # Wait for task
   task_id = response.json().get("task")
   while True:
       status_resp = session.get(f"https://192.168.1.100/api/v4/tasks/{task_id}")
       if status_resp.json()["status"] in ("complete", "error"):
           break
       time.sleep(1)

**With pyvergeos:**

.. code-block:: python

   # Power on
   vm.power_on()

   # With task waiting
   result = vm.snapshot(name="backup")
   task = client.tasks.wait(result["task"], timeout=300)

Error Handling
^^^^^^^^^^^^^^

**Direct API:**

.. code-block:: python

   response = session.get("https://192.168.1.100/api/v4/vms/999")
   if response.status_code == 401:
       # Re-authenticate
       pass
   elif response.status_code == 404:
       raise Exception("Not found")
   elif response.status_code == 409:
       raise Exception("Conflict")
   elif response.status_code >= 400:
       error = response.json().get("error", "Unknown")
       raise Exception(f"API error: {error}")

**With pyvergeos:**

.. code-block:: python

   from pyvergeos.exceptions import (
       AuthenticationError,
       NotFoundError,
       ConflictError,
       APIError,
   )

   try:
       vm = client.vms.get(999)
   except AuthenticationError:
       print("Invalid credentials")
   except NotFoundError:
       print("VM not found")
   except ConflictError:
       print("Resource conflict")
   except APIError as e:
       print(f"API error {e.status_code}: {e.message}")

Filtering
^^^^^^^^^

**Direct API:**

.. code-block:: python

   # Build OData filter manually
   filter_str = "os_family eq 'linux' and ram gt 2048 and status eq 'running'"
   response = session.get(
       "https://192.168.1.100/api/v4/vms",
       params={"filter": filter_str}
   )

**With pyvergeos:**

.. code-block:: python

   # Keyword arguments (recommended for simple filters)
   vms = client.vms.list(os_family="linux", status="running")

   # OData string for complex filters
   vms = client.vms.list(filter="ram gt 2048 and cpu_cores ge 4")

   # Filter builder for programmatic construction
   from pyvergeos.filters import Filter

   f = Filter().eq("os_family", "linux").and_().gt("ram", 2048)
   vms = client.vms.list(filter=str(f))

Common Migration Patterns
-------------------------

Nested Resources
^^^^^^^^^^^^^^^^

Many resources have nested sub-resources accessible via properties:

.. code-block:: python

   # VM drives and NICs
   vm = client.vms.get(name="web-server")
   for drive in vm.drives.list():
       print(f"Drive: {drive.name}, {drive.size} bytes")
   for nic in vm.nics.list():
       print(f"NIC: {nic.name}, MAC {nic.mac}")

   # Network rules
   network = client.networks.get(name="Internal")
   for rule in network.rules.list():
       print(f"Rule: {rule.name}")

   # Tenant storage
   tenant = client.tenants.get(name="customer-a")
   for storage in tenant.storage.list():
       print(f"Storage: {storage.tier}, {storage.allocated} bytes")

Task Waiting
^^^^^^^^^^^^

Replace polling loops with built-in task waiting:

.. code-block:: python

   # Snapshot with wait
   result = vm.snapshot(name="backup", quiesce=True)
   task = client.tasks.wait(result["task"], timeout=300)

   # Custom polling interval
   task = client.tasks.wait(
       result["task"],
       timeout=600,
       poll_interval=5  # Check every 5 seconds
   )

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Use environment variables for configuration:

.. code-block:: bash

   export VERGE_HOST=192.168.1.100
   export VERGE_USERNAME=admin
   export VERGE_PASSWORD=secret
   export VERGE_VERIFY_SSL=false
   export VERGE_TIMEOUT=30
   export VERGE_RETRY_TOTAL=3

.. code-block:: python

   client = VergeClient.from_env()

Checklist
---------

When migrating your code:

1. ☐ Replace ``requests.Session`` with ``VergeClient``
2. ☐ Use context manager for automatic cleanup
3. ☐ Replace manual JSON parsing with typed model objects
4. ☐ Replace status code checks with exception handling
5. ☐ Use keyword arguments for filtering instead of manual filter strings
6. ☐ Replace polling loops with ``client.tasks.wait()``
7. ☐ Access nested resources via properties (e.g., ``vm.drives``)
8. ☐ Use ``iter_all()`` for paginated iteration
9. ☐ Configure via environment variables with ``from_env()``
