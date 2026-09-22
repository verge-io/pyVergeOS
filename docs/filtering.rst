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

   # Wildcard matching: * is any run of characters, ? is exactly one
   web_servers = client.vms.list(name="web-*")

   # A list matches any of several values
   vms = client.vms.list(status=["running", "stopped"])

Filter Strings
--------------

For complex queries, pass a filter expression directly:

.. code-block:: python

   # Greater than
   vms = client.vms.list(filter="ram gt 2048")

   # Compound conditions
   vms = client.vms.list(filter="os_family eq 'linux' and ram gt 2048")

   # Prefix match
   vms = client.vms.list(filter="name bw 'prod-'")

VergeOS filtering is *similar to* OData but is **not** OData. This is the
complete operator set; anything else is rejected with HTTP 422
``Invalid argument``:

.. list-table::
   :header-rows: 1
   :widths: 10 30 25

   * - Operator
     - Meaning
     - Case sensitivity
   * - ``eq``
     - Equal
     - sensitive
   * - ``ne``
     - Not equal
     - sensitive
   * - ``gt`` / ``ge``
     - Greater than / or equal
     -
   * - ``lt`` / ``le``
     - Less than / or equal
     -
   * - ``bw``
     - Begins with
     - sensitive
   * - ``ew``
     - Ends with
     - sensitive
   * - ``cs``
     - Contains
     - sensitive
   * - ``ct``
     - Contains
     - **insensitive**
   * - ``rx``
     - Regular expression, unanchored
     - sensitive
   * - ``and`` / ``or``
     - Logical connectors
     -

.. warning::

   There is no ``like`` and no ``in`` operator, and OData string functions
   such as ``startswith(...)`` and ``contains(...)`` do not exist either. The
   SDK's wildcard and list shorthands are translated to the operators above,
   so prefer them over hand-writing an expression.

   The token ``re`` is accepted by the platform but matches nothing - the
   regex operator is ``rx``.

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
   f = Filter().eq("status", "running").and_().bw("name", "prod-")
   vms = client.vms.list(filter=str(f))

``Filter`` exposes every operator in the grammar - ``eq``, ``ne``, ``gt``,
``ge``, ``lt``, ``le``, ``bw``, ``ew``, ``cs``, ``ct`` and ``rx`` - plus two
shorthands that are translated for you:

.. code-block:: python

   Filter().like("name", "web*")          # -> name bw 'web'
   Filter().in_("status", ["a", "b"])     # -> (status eq 'a' or status eq 'b')

Wildcard Translation
--------------------

``*`` matches any run of characters and ``?`` matches exactly one. Because
VergeOS has no ``like`` operator, patterns are translated to the operators it
does have. Every operator chosen is case-sensitive, so matching does not
change with wildcard position:

.. list-table::
   :header-rows: 1
   :widths: 25 45

   * - Pattern
     - Sent to the API
   * - ``"web"``
     - ``name eq 'web'``
   * - ``"web*"``
     - ``name bw 'web'``
   * - ``"*web"``
     - ``name ew 'web'``
   * - ``"*web*"``
     - ``name cs 'web'``
   * - ``"*"``
     - ``name bw ''`` (matches everything)
   * - ``"a*b"``, ``"web?"``
     - ``name rx '^a.*b$'`` (anchored regex)

Lists expand to a parenthesised ``or`` chain, and wildcards inside a list are
translated per element:

.. code-block:: python

   client.vms.list(status=["running", "stopped"])
   # -> (status eq 'running' or status eq 'stopped')

   client.vms.list(name=["web*", "db*"])
   # -> (name bw 'web' or name bw 'db')

An empty list raises ``ValueError`` rather than silently matching nothing.

.. note::

   ``%`` and ``_`` are ordinary literal characters, not wildcards. There is no
   escape for a literal ``*`` or ``?`` in the shorthand - to match those
   exactly, use ``get(name=...)`` or a raw ``filter=`` expression with
   ``quote_value()``.

   Wildcards only apply to text columns. A wildcard against a numeric column
   is accepted by the platform but matches nothing.

String Values
-------------

Pass unescaped values to ``get(name=...)``, keyword filters, and ``Filter``.
The SDK quotes apostrophes and backslashes using VergeOS's backslash escaping:

.. code-block:: python

   group = client.groups.get(name="O'Brien")
   groups = client.groups.list(name="O'Brien")
   f = Filter().eq("path", r"C:\O'Brien\share")

When composing a raw ``filter=`` expression, use ``quote_value`` for string
literals. It includes the surrounding quotes and preserves wildcard characters:

.. code-block:: python

   from pyvergeos.filters import quote_value

   name = "O'Brien"
   groups = client.groups.list(filter=f"name eq {quote_value(name)}")

Raw ``filter=`` strings are sent unchanged. SQL-style doubled apostrophes are
not valid VergeOS escaping. ``get(name=...)`` matches names exactly, treating
``*`` and ``?`` as literal characters; keyword filters and ``Filter.like()``
apply the wildcard translation described above.

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
