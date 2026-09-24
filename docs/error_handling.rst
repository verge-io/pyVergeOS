Error Handling
==============

pyvergeos provides a comprehensive exception hierarchy for handling errors.

Exception Hierarchy
-------------------

.. code-block:: text

   VergeError (base exception)
   ├── VergeConnectionError - Connection failures
   ├── VergeTimeoutError - Request timeouts
   ├── NotConnectedError - Operation without an active connection
   ├── FieldNotProjectedError - Field read but never requested
   └── APIError - API-level errors
       ├── AuthenticationError - 401/403 errors
       ├── NotFoundError - 404 errors
       ├── ValidationError - 400 errors
       ├── ConflictError - 409 errors
       └── TaskError - Task failures
           └── TaskTimeoutError - Task timeout

Basic Error Handling
--------------------

.. code-block:: python

   from pyvergeos import VergeClient
   from pyvergeos.exceptions import (
       VergeError,
       NotFoundError,
       AuthenticationError,
       ValidationError,
   )

   try:
       client = VergeClient(host="192.168.1.100", username="admin", password="wrong")
   except AuthenticationError:
       print("Invalid credentials")

   try:
       vm = client.vms.get(name="nonexistent")
   except NotFoundError:
       print("VM not found")

Unprojected Fields
------------------

Accessors such as ``is_running``, ``status`` and ``member_count`` read a field
the manager asked the API for. Narrow ``fields`` and the field is not in the
row, so the accessor raises ``FieldNotProjectedError`` rather than answering
``False`` or ``""`` -- a wrong answer indistinguishable from a real one, and
the wrong direction for a guard in front of a destructive operation.

.. code-block:: python

   from pyvergeos.exceptions import FieldNotProjectedError

   vm = client.vms.get(name="web-01", fields=["$key", "name"])
   try:
       if vm.is_running:
           ...
   except FieldNotProjectedError as exc:
       print(f"{exc.field} was not fetched; re-read with the default fields")

Any of these give a usable answer:

.. code-block:: python

   vm = client.vms.get(name="web-01")                              # default fields
   vm = client.vms.get(name="web-01", fields=["all"])              # expanded for you
   vm = client.vms.get(name="web-01", fields=["$key", "running"])  # name the field

Naming the field is safe even though the API has a ``running`` column of its
own that is null on every row: the SDK sends the manager's definition of that
name, not the bare column.

.. note::

   ``FieldNotProjectedError`` is deliberately **not** an ``AttributeError``,
   so ``getattr(vm, "is_running", None)`` and ``hasattr(vm, "is_running")``
   propagate it instead of quietly answering ``None``/``False``. Were it an
   ``AttributeError``, the dict attribute fallback would swallow it and
   ``hasattr()`` would report ``False`` for a field that exists but was not
   fetched -- the same silent wrong answer in a new place. Catch the
   exception, or test membership with ``"running" in vm``.

Connection Errors
-----------------

.. code-block:: python

   from pyvergeos.exceptions import VergeConnectionError, VergeTimeoutError

   try:
       client = VergeClient(host="unreachable.host", username="admin", password="secret")
   except VergeConnectionError as e:
       print(f"Could not connect: {e}")
   except VergeTimeoutError as e:
       print(f"Connection timed out: {e}")

API Errors
----------

.. code-block:: python

   from pyvergeos.exceptions import APIError, ValidationError, ConflictError

   try:
       # Invalid parameters
       vm = client.vms.create(name="", ram=-1)
   except ValidationError as e:
       print(f"Invalid input: {e}")
       print(f"Status code: {e.status_code}")

   try:
       # Resource already exists
       vm = client.vms.create(name="existing-vm")
   except ConflictError as e:
       print(f"Conflict: {e}")

Error bodies are available separately from the message as ``response_body`` on
``APIError`` and its subclasses. JSON responses retain the entire decoded value,
including VergeOS's generic top-level ``response`` payload. Non-JSON responses
retain raw text (an empty body is ``""``). Errors constructed without a body have
``response_body=None``. Existing message and status-code handling is unchanged.

.. code-block:: python

   try:
       client.vm_recipe_instances.create(
           recipe=recipe.key, name="preview-vm", answers=answers, simulate=True
       )
   except APIError as exc:
       body = exc.response_body
       if isinstance(body, dict):
           details = body.get("response")
           # Inspect details locally; reports can contain guest credentials.

For recipe practice runs, prefer ``vm_recipe_instances.simulate()`` as shown in
:ref:`vm-recipe-simulation`; it returns the report for the documented completion
response and propagates other errors.

Read-only Fields in Settings Updates
------------------------------------

A response can contain fields that the API rejects in a PUT body. Pass only
the fields you intend to change; do not send a fetched row back as the update
payload. SDK manager methods use the record identifier in the URL.

For example, system settings updates send only ``value``:

.. code-block:: python

   client.system.settings.update("ntp_servers", "0.pool.ntp.org 1.pool.ntp.org")

Alternatively, ``save()`` accepts explicit changes rather than replaying the
fetched row:

.. code-block:: python

   setting = client.system.settings.get("ntp_servers")
   setting.save(value="0.pool.ntp.org 1.pool.ntp.org")

An NTP settings write can restart the service even when the value is unchanged.
Allow the restart to finish before issuing another NTP settings write.

The related API endpoints have their own read-only fields:

.. list-table:: Fields to omit from PUT bodies
   :header-rows: 1
   :widths: 45 55

   * - Endpoint
     - Read-only fields
   * - ``settings``
     - ``key``, ``default_value``
   * - ``task_settings``, ``schedule_task_settings``
     - ``key``
   * - ``meta_data``
     - ``key``, ``default_value``, ``created``, ``creator``
   * - ``user_settings``
     - ``user``, ``modified``
   * - ``resource_group_settings_*``
     - ``resource_group``, ``modified``
   * - ``smtp_settings``
     - ``name``
   * - ``update_settings``
     - ``installed``, ``reboot_required``, ``applying_updates``,
       ``applying_updates_force``, ``release_notes_url``

The SDK currently has no dedicated managers for ``task_settings`` or
``schedule_task_settings``. ``client.tasks.update(..., settings_args={...})``
updates task settings through the parent ``tasks`` endpoint.

Read-only rules are endpoint-specific: the ``licenses`` resource, for example,
has a writable ``key`` field containing the license key. Do not strip fields
named ``key`` indiscriminately or remove foreign keys that are editable.

Task Errors
-----------

``client.tasks`` is the VergeOS task scheduler. Waiting applies to a scheduled
task you run, and raises on timeout or failure:

.. code-block:: python

   from pyvergeos.exceptions import TaskError, TaskTimeoutError

   task = client.tasks.get(name="Nightly backup")

   try:
       task.execute()
       task.wait(timeout=300)
   except TaskTimeoutError as e:
       print(f"Task {e.task_id} did not finish in time")
   except TaskError as e:
       print(f"Task failed: {e}")

Most VergeOS operations finish on the API call itself and never create a task
row, so do not look for a task key in a response. Where an operation really is
asynchronous, the manager takes its own ``wait`` argument:

.. code-block:: python

   from pyvergeos.exceptions import VergeTimeoutError

   try:
       snapshot = client.cloud_snapshots.create(name="nightly", wait=True, wait_timeout=600)
   except VergeTimeoutError:
       print("Snapshot did not settle within the timeout")

Catching All Errors
-------------------

Use the base ``VergeError`` to catch any pyvergeos exception:

.. code-block:: python

   from pyvergeos.exceptions import VergeError

   try:
       # Any pyvergeos operation
       vm = client.vms.get(123)
       vm.power_on()
   except VergeError as e:
       print(f"Operation failed: {e}")

Retry Configuration
-------------------

pyvergeos automatically retries transient errors (429, 500, 502, 503, 504):

.. code-block:: python

   from http import HTTPStatus

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       retry_total=5,              # Number of retries (default: 3)
       retry_backoff_factor=2.0,   # Exponential backoff (default: 1)
       retry_status_codes=frozenset({  # Codes to retry
           HTTPStatus.TOO_MANY_REQUESTS,
           HTTPStatus.SERVICE_UNAVAILABLE,
       }),
   )

   # Disable retries
   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       retry_total=0,
   )

Exception Attributes
--------------------

API exceptions include useful attributes:

.. code-block:: python

   try:
       vm = client.vms.get(999999)
   except NotFoundError as e:
       print(f"Message: {e}")
       print(f"Status code: {e.status_code}")  # 404
