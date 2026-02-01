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
