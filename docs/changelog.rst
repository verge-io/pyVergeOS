Changelog
=========

All notable changes to pyvergeos will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

Added
^^^^^

- Sphinx documentation with API reference
- GitHub Pages deployment workflow

[0.1.1] - 2026-01-29
--------------------

Added
^^^^^

- Configurable retry strategy for HTTP requests
- System enhancements for diagnostics, certificates, and settings
- Unit tests for remaining resource managers

[0.1.0] - 2026-01-15
--------------------

Initial release.

Added
^^^^^

- Core client with username/password and token authentication
- Virtual machine management (CRUD, power operations, snapshots)
- Network management (CRUD, firewall rules, DNS)
- Tenant management
- NAS/storage management
- User and group management
- Task monitoring and waiting
- OData filter builder
- Automatic retry with exponential backoff
- Comprehensive exception hierarchy
- Full type annotations
