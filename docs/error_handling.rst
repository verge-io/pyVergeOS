Error Handling
==============

pyvergeos provides a comprehensive exception hierarchy for handling errors.

Exception Hierarchy
-------------------

.. code-block:: text

   VergeError (base exception)
   ├── VergeConnectionError - Connection failures
   ├── VergeTimeoutError - Request timeouts
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

Long-running operations return task references. Use ``tasks.wait()`` to wait for completion:

.. code-block:: python

   from pyvergeos.exceptions import TaskError, TaskTimeoutError

   try:
       # Wait for a snapshot to complete
       result = vm.snapshot(name="backup")
       task = client.tasks.wait(result["task"], timeout=300)
   except TaskTimeoutError as e:
       print(f"Task {e.task_id} timed out after {e.timeout}s")
   except TaskError as e:
       print(f"Task failed: {e}")

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
