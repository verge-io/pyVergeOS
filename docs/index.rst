pyvergeos Documentation
=======================

**pyvergeos** is the official Python SDK for the VergeOS REST API.

It provides a Pythonic interface for managing VergeOS infrastructure, including
virtual machines, networks, storage, tenants, and more.

.. code-block:: python

   from pyvergeos import VergeClient

   with VergeClient(host="192.168.1.100", username="admin", password="secret") as client:
       # List all running VMs
       for vm in client.vms.list(status="running"):
           print(f"{vm.name}: {vm.ram}MB RAM")

       # Create a new VM
       vm = client.vms.create(name="web-server", ram=4096, cpu_cores=2)
       vm.power_on()

Features
--------

- **Full API Coverage** - Access all VergeOS API v4 endpoints
- **Type Safety** - Complete type annotations for IDE autocompletion
- **Pythonic Interface** - Intuitive, idiomatic Python API
- **Production Ready** - Robust error handling, retries, and logging

Requirements
------------

- Python 3.9+
- VergeOS 26.0+

Installation
------------

.. code-block:: bash

   pip install pyvergeos

   # Or with uv
   uv add pyvergeos

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   quickstart
   authentication
   filtering
   error_handling
   tutorials

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/client
   api/resources
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   migration
   troubleshooting
   changelog
   contributing

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
