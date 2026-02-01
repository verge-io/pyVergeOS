Troubleshooting
===============

This guide helps you diagnose and resolve common issues with pyvergeos.

.. contents:: Contents
   :local:
   :depth: 2

Connection Issues
-----------------

SSL Certificate Errors
^^^^^^^^^^^^^^^^^^^^^^

**Symptom:** ``SSLError: certificate verify failed``

**Cause:** Self-signed or untrusted SSL certificates.

**Solution:** Disable SSL verification for development/testing:

.. code-block:: python

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       verify_ssl=False  # Disable SSL verification
   )

Or via environment variable:

.. code-block:: bash

   export VERGE_VERIFY_SSL=false

.. warning::

   Only disable SSL verification in trusted environments. For production,
   configure proper certificates on your VergeOS system.

Connection Timeout
^^^^^^^^^^^^^^^^^^

**Symptom:** ``VergeTimeoutError: Connection timed out``

**Cause:** Network issues, firewall blocking, or slow server response.

**Solutions:**

1. Increase the timeout:

   .. code-block:: python

      client = VergeClient(
          host="192.168.1.100",
          username="admin",
          password="secret",
          timeout=60  # Increase to 60 seconds
      )

2. Check network connectivity:

   .. code-block:: bash

      ping 192.168.1.100
      curl -k https://192.168.1.100/api/v4/auth

3. Verify firewall rules allow HTTPS (port 443).

Connection Refused
^^^^^^^^^^^^^^^^^^

**Symptom:** ``VergeConnectionError: Connection refused``

**Cause:** VergeOS API service not running or wrong port.

**Solutions:**

1. Verify the VergeOS UI is accessible in a browser.
2. Check if the API is responding:

   .. code-block:: bash

      curl -k https://192.168.1.100/api/v4/

3. Ensure you're using HTTPS (not HTTP).

Authentication Errors
---------------------

Invalid Credentials
^^^^^^^^^^^^^^^^^^^

**Symptom:** ``AuthenticationError: Invalid username or password``

**Solutions:**

1. Verify credentials work in the VergeOS UI.
2. Check for special characters that may need escaping.
3. Ensure the user account is not locked or disabled.

API Token Issues
^^^^^^^^^^^^^^^^

**Symptom:** ``AuthenticationError`` when using token authentication.

**Solutions:**

1. Verify the token hasn't expired.
2. Generate a new API token in VergeOS UI (Users > API Keys).
3. Use the full token string:

   .. code-block:: python

      client = VergeClient(
          host="192.168.1.100",
          token="your-full-api-token-string"
      )

Permission Denied
^^^^^^^^^^^^^^^^^

**Symptom:** ``AuthenticationError: Permission denied`` or 403 errors.

**Cause:** User lacks permissions for the requested operation.

**Solutions:**

1. Check user permissions in VergeOS UI.
2. Ensure the user has the required role (admin, operator, etc.).
3. For tenant-scoped operations, verify access to the specific tenant.

Resource Errors
---------------

Resource Not Found
^^^^^^^^^^^^^^^^^^

**Symptom:** ``NotFoundError: Resource not found``

**Common Causes:**

1. Resource was deleted.
2. Wrong resource ID or name.
3. Resource is in a different tenant.

**Solutions:**

.. code-block:: python

   from pyvergeos.exceptions import NotFoundError

   try:
       vm = client.vms.get(name="my-vm")
   except NotFoundError:
       # List available VMs to find the right one
       vms = client.vms.list()
       for v in vms:
           print(f"{v.key}: {v.name}")

Conflict Errors
^^^^^^^^^^^^^^^

**Symptom:** ``ConflictError: Resource conflict``

**Causes:**

1. Resource with same name already exists.
2. Resource is in use by another operation.
3. Resource state prevents the operation (e.g., deleting a running VM).

**Solutions:**

.. code-block:: python

   from pyvergeos.exceptions import ConflictError

   try:
       vm = client.vms.create(name="web-server", ram=2048)
   except ConflictError:
       # Check if VM already exists
       existing = client.vms.list(name="web-server")
       if existing:
           vm = existing[0]
       else:
           raise

Validation Errors
^^^^^^^^^^^^^^^^^

**Symptom:** ``ValidationError: Invalid field value``

**Cause:** Invalid parameters passed to the API.

**Solutions:**

1. Check parameter types (int vs string).
2. Verify required fields are provided.
3. Ensure values are within valid ranges.

.. code-block:: python

   # Wrong: RAM as string
   vm = client.vms.create(name="test", ram="2048")

   # Correct: RAM as integer
   vm = client.vms.create(name="test", ram=2048)

Task and Operation Errors
-------------------------

Task Timeout
^^^^^^^^^^^^

**Symptom:** ``TaskTimeoutError: Task timed out``

**Cause:** Long-running operation didn't complete in time.

**Solutions:**

1. Increase timeout:

   .. code-block:: python

      task = client.tasks.wait(task_id, timeout=600)  # 10 minutes

2. Check task status manually:

   .. code-block:: python

      task = client.tasks.get(task_id)
      print(f"Status: {task.status}")
      print(f"Progress: {task.percent_complete}%")

3. Check VergeOS logs for the operation.

Task Failed
^^^^^^^^^^^

**Symptom:** ``TaskError: Task failed`` or task status is "error".

**Solutions:**

1. Check task error message:

   .. code-block:: python

      task = client.tasks.get(task_id)
      print(f"Error: {task.error_message}")

2. View task logs in VergeOS UI (System > Tasks).

3. Check system logs for more details:

   .. code-block:: python

      logs = client.logs.list(
          filter="task_id eq " + str(task_id),
          limit=50
      )
      for log in logs:
          print(f"[{log.level}] {log.text}")

Performance Issues
------------------

Slow Responses
^^^^^^^^^^^^^^

**Cause:** Large result sets, network latency, or server load.

**Solutions:**

1. Use pagination:

   .. code-block:: python

      # Don't fetch all at once
      vms = client.vms.list(limit=100, offset=0)

      # Use iter_all for memory efficiency
      for vm in client.vms.iter_all(page_size=100):
          process(vm)

2. Select only needed fields:

   .. code-block:: python

      vms = client.vms.list(fields=["name", "status", "ram"])

3. Use specific filters to reduce results:

   .. code-block:: python

      # Instead of filtering client-side
      running_vms = [vm for vm in client.vms.list() if vm.status == "running"]

      # Filter server-side
      running_vms = client.vms.list(status="running")

Memory Usage
^^^^^^^^^^^^

**Symptom:** High memory usage when processing many resources.

**Solution:** Use iterators instead of loading all results:

.. code-block:: python

   # Memory-heavy: loads all into memory
   all_vms = client.vms.list()

   # Memory-efficient: processes one at a time
   for vm in client.vms.iter_all():
       process(vm)

Retry Behavior
--------------

Configuring Retries
^^^^^^^^^^^^^^^^^^^

pyvergeos automatically retries on transient errors (429, 500, 502, 503, 504).

**Customize retry behavior:**

.. code-block:: python

   from http import HTTPStatus

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       retry_total=5,              # Max retry attempts
       retry_backoff_factor=2.0,   # Exponential backoff
       retry_status_codes=frozenset({
           HTTPStatus.TOO_MANY_REQUESTS,
           HTTPStatus.SERVICE_UNAVAILABLE,
       }),
   )

**Disable retries:**

.. code-block:: python

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       retry_total=0,  # No retries
   )

Debugging
---------

Enable Debug Logging
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import logging

   # Enable debug logging
   logging.basicConfig(level=logging.DEBUG)
   logging.getLogger("pyvergeos").setLevel(logging.DEBUG)

   # Now all requests/responses are logged
   client = VergeClient.from_env()
   vms = client.vms.list()

Inspect Request/Response
^^^^^^^^^^^^^^^^^^^^^^^^

For advanced debugging, use a requests hook:

.. code-block:: python

   from pyvergeos.connection import Connection

   def log_response(response, *args, **kwargs):
       print(f"Request: {response.request.method} {response.request.url}")
       print(f"Response: {response.status_code}")
       print(f"Body: {response.text[:500]}")

   # Add hook to connection
   client._connection._session.hooks["response"].append(log_response)

Getting Help
------------

If you're still having issues:

1. Check the `GitHub Issues <https://github.com/verge-io/pyvergeos/issues>`_
2. Search existing issues for similar problems
3. Open a new issue with:

   - pyvergeos version (``pip show pyvergeos``)
   - Python version
   - VergeOS version
   - Full error traceback
   - Minimal code to reproduce the issue
