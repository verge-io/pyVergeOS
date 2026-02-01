Authentication
==============

pyvergeos supports multiple authentication methods for connecting to VergeOS.

Username and Password
---------------------

The most common method uses your VergeOS username and password:

.. code-block:: python

   from pyvergeos import VergeClient

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret"
   )

API Token
---------

For automated scripts and CI/CD pipelines, API tokens are recommended:

.. code-block:: python

   client = VergeClient(
       host="192.168.1.100",
       token="your-api-token"
   )

To create an API token in VergeOS:

1. Navigate to **System** > **Users**
2. Select your user
3. Click **API Keys** tab
4. Click **New** to create a token

Environment Variables
---------------------

For security, credentials can be provided via environment variables:

.. code-block:: bash

   export VERGE_HOST=192.168.1.100
   export VERGE_USERNAME=admin
   export VERGE_PASSWORD=secret

   # Or use a token
   export VERGE_TOKEN=your-api-token

   # Optional settings
   export VERGE_VERIFY_SSL=false
   export VERGE_TIMEOUT=30

Then connect without explicit credentials:

.. code-block:: python

   from pyvergeos import VergeClient

   client = VergeClient.from_env()

SSL Certificate Verification
----------------------------

By default, SSL certificates are verified. For self-signed certificates:

.. code-block:: python

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       verify_ssl=False  # Disable verification for self-signed certs
   )

.. warning::

   Disabling SSL verification is not recommended for production environments.

Connection Options
------------------

Additional connection options:

.. code-block:: python

   client = VergeClient(
       host="192.168.1.100",
       username="admin",
       password="secret",
       timeout=60,              # Request timeout in seconds (default: 30)
       retry_total=5,           # Number of retry attempts (default: 3)
       retry_backoff_factor=2,  # Exponential backoff factor (default: 1)
   )

Checking Connection Status
--------------------------

.. code-block:: python

   # Check if connected
   if client.is_connected:
       print("Connected to VergeOS")

   # Get connection info
   info = client.connection_info
   print(f"Host: {info['host']}")
   print(f"User: {info['username']}")

Disconnecting
-------------

Always disconnect when finished:

.. code-block:: python

   client.disconnect()

Or use a context manager for automatic cleanup:

.. code-block:: python

   with VergeClient(host="...", username="...", password="...") as client:
       # Work with VergeOS
       pass
   # Automatically disconnected
