Filtering and Pagination
========================

pyvergeos provides flexible options for filtering and paginating results.

Keyword Arguments
-----------------

The simplest way to filter is with keyword arguments:

.. code-block:: python

   # Filter by status
   running_vms = client.vms.list(status="running")

   # Filter by multiple fields
   linux_vms = client.vms.list(os_family="linux", status="running")

   # Wildcard matching
   web_servers = client.vms.list(name="web-*")

OData Filter Strings
--------------------

For complex queries, use OData filter syntax:

.. code-block:: python

   # Greater than
   vms = client.vms.list(filter="ram gt 2048")

   # Compound conditions
   vms = client.vms.list(filter="os_family eq 'linux' and ram gt 2048")

   # String functions
   vms = client.vms.list(filter="startswith(name, 'prod-')")

Supported operators:

- ``eq`` - Equal
- ``ne`` - Not equal
- ``gt`` - Greater than
- ``lt`` - Less than
- ``ge`` - Greater than or equal
- ``le`` - Less than or equal
- ``and`` - Logical and
- ``or`` - Logical or

Filter Builder
--------------

For programmatic filter construction, use the ``Filter`` class:

.. code-block:: python

   from pyvergeos.filters import Filter

   # Build a filter
   f = Filter()
   f.eq("os_family", "linux")
   f.and_()
   f.gt("ram", 2048)

   vms = client.vms.list(filter=str(f))

   # Method chaining
   f = Filter().eq("status", "running").and_().startswith("name", "prod-")
   vms = client.vms.list(filter=str(f))

Field Selection
---------------

Limit returned fields for better performance:

.. code-block:: python

   # Only return name and status
   vms = client.vms.list(fields=["name", "status"])

   for vm in vms:
       print(f"{vm.name}: {vm.status}")

Pagination
----------

Control result size with ``limit`` and ``offset``:

.. code-block:: python

   # Get first 10 results
   vms = client.vms.list(limit=10)

   # Get next 10 results
   vms = client.vms.list(limit=10, offset=10)

Iterating All Results
---------------------

For large result sets, use ``iter_all()`` for automatic pagination:

.. code-block:: python

   # Automatically handles pagination
   for vm in client.vms.iter_all():
       print(vm.name)

   # Custom page size
   for vm in client.vms.iter_all(page_size=50):
       process(vm)

Sorting
-------

Sort results with the ``orderby`` parameter:

.. code-block:: python

   # Sort by name ascending
   vms = client.vms.list(orderby="name")

   # Sort descending
   vms = client.vms.list(orderby="name desc")

   # Multiple sort fields
   vms = client.vms.list(orderby="status,name")

Combining Options
-----------------

All filtering and pagination options can be combined:

.. code-block:: python

   vms = client.vms.list(
       filter="os_family eq 'linux'",
       fields=["name", "status", "ram"],
       orderby="name",
       limit=100
   )
