Contributing
============

Thank you for your interest in contributing to pyvergeos!

Development Setup
-----------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/verge-io/pyvergeos.git
      cd pyvergeos

2. Install dependencies with uv:

   .. code-block:: bash

      uv sync

3. Run tests:

   .. code-block:: bash

      uv run pytest tests/unit

Code Style
----------

We use ``ruff`` for linting and formatting:

.. code-block:: bash

   # Lint and auto-fix
   uv run ruff check --fix .

   # Format
   uv run ruff format .

   # Type check
   uv run mypy pyvergeos

Guidelines
----------

- **Line length**: 100 characters maximum
- **Docstrings**: Google style for all public classes and methods
- **Type hints**: Required for all public APIs
- **Tests**: Required for new features and bug fixes

Adding a Resource Accessor
--------------------------

A field the server has to *compute* -- a traversal like
``machine#status#running as running`` or an aggregate like
``count(members) as member_count`` -- is not part of ``fields=all``. It
arrives only if the manager asked for it by name.

Declare the accessor and the projection entry behind it together, with
``Projected``, so the two cannot drift apart:

.. code-block:: python

   from pyvergeos.resources.base import Projected

   class Network(ResourceObject):
       is_running = Projected[bool](
           "machine#status#running as running",
           bool,
           default=False,
           doc="Check if network is powered on.",
       )

The manager then derives its projection from the declarations rather than
restating them:

.. code-block:: python

   DEFAULT_NETWORK_FIELDS = [*_NETWORK_COLUMNS, *Network.projected_entries()]

Adding the accessor is therefore all that is needed; its field joins every
query that reads it.

Do **not** write the accessor by hand::

   # wrong: nothing ties this to the manager's field list, and it cannot
   # tell a stopped network from one whose 'running' was never fetched
   @property
   def is_running(self) -> bool:
       return bool(self.get("running", False))

A test enforces this: no ``@property`` may call ``require_projected``.

Arguments
^^^^^^^^^

The read happens in a fixed order, which is what lets ``Projected``
reproduce the hand-written accessors it replaced:

1. ``require_projected(alias, default)``
2. ``fallback`` -- re-read from a plain field when the value is falsy
3. ``falsy`` -- substitute for any falsy value, the ``x or 0`` idiom
4. ``null`` -- return this, uncoerced, when the value is None
5. ``coerce``, then ``transform``

``default`` answers the case where the field *was* requested but the server
omitted it, which happens when a traversal passes through a null
polymorphic reference. If the field was never requested at all, the
accessor raises ``FieldNotProjectedError`` rather than guessing.

Note that ``coerce`` receives a null value unless ``null`` is given. That is
deliberate -- it is what the accessors being replaced did.

``transform`` covers display maps and unit conversions:

.. code-block:: python

   from pyvergeos.resources.base import display_map, epoch_utc

   status = Projected[str](
       "status#status as status", str, default="",
       transform=display_map(STATUS_DISPLAY),
   )
   started_at = Projected["datetime | None"](
       "machine#status#started as started",
       falsy=None, null=None, transform=epoch_utc,
   )

Write a union parameter as a string -- ``Projected["str | None"]`` -- because
the subscript is evaluated at runtime and ``str | None`` is a ``TypeError``
on Python 3.9, which is still supported.

Plain columns are different: read them with ``self.get()`` as usual. ``all``
already covers them, so there is nothing to keep in step.

References
^^^^^^^^^^

Some columns hold a ``"table/key"`` reference such as ``"vms/39"``, and a key
is not always numeric -- recipes are keyed by name. Use
``reference_key()``/``reference_table()`` rather than ``int()``:

.. code-block:: python

   from pyvergeos.resources.base import reference_key

   @property
   def owner_key(self) -> str | int | None:
       return reference_key(self.get("owner"))

Running Tests
-------------

.. code-block:: bash

   # Unit tests only
   uv run pytest tests/unit

   # With coverage
   uv run pytest tests/unit --cov=pyvergeos

   # Specific test file
   uv run pytest tests/unit/test_vms.py

   # Pattern matching
   uv run pytest -k "test_vm"

Pull Request Process
--------------------

1. Create a feature branch from ``main``
2. Make your changes with tests
3. Ensure all tests pass and linting is clean
4. Submit a pull request with a clear description

Commit Messages
---------------

We use conventional commits with emoji:

- ``feat:`` New feature
- ``fix:`` Bug fix
- ``docs:`` Documentation changes
- ``test:`` Test additions or fixes
- ``refactor:`` Code refactoring

Example:

.. code-block:: text

   feat: add VM migration support

   - Add migrate() method to VM class
   - Add integration tests for live migration
