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
