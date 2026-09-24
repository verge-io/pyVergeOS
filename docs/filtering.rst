Filtering and Pagination
========================

pyvergeos provides flexible options for filtering and paginating results.

Keyword Arguments
-----------------

The simplest way to filter is with keyword arguments:

.. code-block:: python

   # Filter by a single field
   linux_vms = client.vms.list(os_family="linux")

   # Filter by multiple fields
   big_linux_vms = client.vms.list(os_family="linux", cpu_cores=8)

   # Power state lives on a joined field that the API cannot filter on, so
   # the SDK provides helpers that sort it out for you
   running_vms = client.vms.list_running()

   # Wildcard matching (* = any run of characters, ? = one character).
   # VergeOS has no LIKE operator; the SDK translates wildcards to the
   # platform's bw/ew/cs/rx operators. Matching is case-sensitive.
   web_servers = client.vms.list(name="web-*")

   # Membership: expands to a parenthesized or-chain of eq conditions
   # (VergeOS has no IN operator). Raises ValueError for an empty list.
   vms = client.vms.list(name=["web-01", "web-02"])

OData Filter Strings
--------------------

For complex queries, use OData filter syntax:

.. code-block:: python

   # Greater than
   vms = client.vms.list(filter="ram gt 2048")

   # Compound conditions
   vms = client.vms.list(filter="os_family eq 'linux' and ram gt 2048")

   # Prefix / substring / regex
   vms = client.vms.list(filter="name bw 'prod-'")
   vms = client.vms.list(filter="name ct 'web'")
   vms = client.vms.list(filter="name rx '^prod-[0-9]+$'")

Supported operators. The platform grammar is "similar to OData" rather than
OData itself, so ``like``, ``in`` and function calls such as ``startswith()``
are rejected with HTTP 422:

- ``eq`` / ``ne`` - Equal / not equal
- ``gt`` / ``ge`` / ``lt`` / ``le`` - Numeric comparisons
- ``bw`` / ``ew`` - Begins with / ends with (case-sensitive)
- ``cs`` / ``ct`` - Contains (``cs`` case-sensitive, ``ct`` case-insensitive)
- ``rx`` - POSIX-ERE regex, partial match, case-sensitive. Bracket classes
  (``[0-9]``, ``[[:digit:]]``) work; PCRE shorthands (``\d``) and inline
  flags (``(?i)``) silently match nothing, and an empty pattern matches
  every row.
- ``and`` / ``or`` - Logical connectors. **There is no operator precedence**:
  expressions evaluate strictly left-to-right, so always parenthesize
  ``or`` groups embedded in larger filters.

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

   # Method chaining (AND is implicit between conditions)
   f = Filter().eq("os_family", "linux").bw("name", "prod-")
   vms = client.vms.list(filter=str(f))

   # Native operators: bw, ew, cs, ct, rx
   f = Filter().ct("description", "database").rx("name", "^db-[0-9]+$")

   # Wildcards and lists are translated to supported operators
   f = Filter().like("name", "web-*")        # -> name bw 'web-'
   f = Filter().in_("name", ["a", "b"])     # -> (name eq 'a' or name eq 'b')

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
not valid VergeOS escaping. ``get(name=...)`` matches names exactly. In
keyword filters and ``Filter.like()``, ``*`` and ``?`` are wildcards and are
translated to supported operators (``foo*`` -> ``bw``, ``*foo`` -> ``ew``,
``*foo*`` -> ``cs``, complex patterns -> anchored ``rx`` with metacharacters
escaped). ``%`` and ``_`` are ordinary literal characters. All wildcard
matching is case-sensitive; use ``filter="field ct '...'"`` or
``Filter().ct(...)`` for case-insensitive contains.

Field Selection
---------------

Limit returned fields for better performance. ``fields`` accepts a list of
names or the API's native comma-separated string, and both send the same
request (previously the string form was joined character by character and
silently returned empty rows, issue #101):

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

``list()`` takes no sort argument. Any unrecognized keyword is treated as a
filter condition, so passing something like ``orderby="name"`` quietly builds
``orderby eq 'name'`` and the query fails or returns nothing.

Where ordering matters, the SDK already applies it. Drives, NICs and firewall
rules come back in configured order, and history endpoints come back newest
first. For anything else, sort in Python:

.. code-block:: python

   vms = sorted(client.vms.list(), key=lambda vm: vm.name)

Combining Options
-----------------

Filtering, field selection and pagination can be combined:

.. code-block:: python

   vms = client.vms.list(
       filter="os_family eq 'linux'",
       fields=["name", "status", "ram"],
       limit=100
   )
