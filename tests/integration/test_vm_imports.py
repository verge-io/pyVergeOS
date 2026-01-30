"""Integration tests for VM import operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestVmImportManagerIntegration:
    """Integration tests for VmImportManager."""

    def test_list_vm_imports(self, live_client: VergeClient) -> None:
        """Test listing VM imports from live system."""
        imports = live_client.vm_imports.list()

        # Should return a list (may be empty)
        assert isinstance(imports, list)

        # Each item should be a VmImport object
        for imp in imports:
            assert hasattr(imp, "name")
            assert hasattr(imp, "status")
            assert hasattr(imp, "key")
            # Key should be a string (40-char hex)
            assert isinstance(imp.key, str)
            assert len(imp.key) == 40

    def test_list_vm_imports_with_pagination(self, live_client: VergeClient) -> None:
        """Test listing VM imports with pagination."""
        # Get first page
        imports = live_client.vm_imports.list(limit=5)

        # Should return a list
        assert isinstance(imports, list)
        assert len(imports) <= 5

    def test_list_vm_imports_by_status(self, live_client: VergeClient) -> None:
        """Test filtering VM imports by status."""
        # Get all imports
        all_imports = live_client.vm_imports.list()

        # Filter by complete status
        complete_imports = live_client.vm_imports.list(status="complete")

        # Each should have complete status
        for imp in complete_imports:
            assert imp.status == "complete"

        # Should be fewer or equal to total
        assert len(complete_imports) <= len(all_imports)

    def test_get_vm_import_by_key(self, live_client: VergeClient) -> None:
        """Test getting a VM import by key."""
        imports = live_client.vm_imports.list(limit=1)
        if not imports:
            pytest.skip("No VM imports available")

        imp = live_client.vm_imports.get(key=imports[0].key)

        assert imp.key == imports[0].key
        assert imp.name == imports[0].name

    def test_get_vm_import_not_found(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent import."""
        with pytest.raises(NotFoundError):
            live_client.vm_imports.get(key="0" * 40)

    def test_vm_import_properties(self, live_client: VergeClient) -> None:
        """Test VM import property accessors on live data."""
        imports = live_client.vm_imports.list(limit=1)
        if not imports:
            pytest.skip("No VM imports available")

        imp = imports[0]

        # Basic properties should be accessible
        assert isinstance(imp.name, str)
        assert isinstance(imp.status, str)
        assert imp.status in [
            "initializing",
            "importing",
            "complete",
            "aborted",
            "error",
            "warning",
        ]
        assert isinstance(imp.is_complete, bool)
        assert isinstance(imp.is_importing, bool)
        assert isinstance(imp.has_error, bool)

    def test_vm_import_logs_access(self, live_client: VergeClient) -> None:
        """Test accessing VM import logs via the import object."""
        imports = live_client.vm_imports.list(limit=1)
        if not imports:
            pytest.skip("No VM imports available")

        imp = imports[0]

        # Get logs for this import
        logs = imp.logs.list()

        # Should return a list
        assert isinstance(logs, list)

        # Each log should have expected properties
        for log in logs:
            assert hasattr(log, "level")
            assert hasattr(log, "text")


@pytest.mark.integration
class TestVmImportLogManagerIntegration:
    """Integration tests for VmImportLogManager."""

    def test_list_vm_import_logs(self, live_client: VergeClient) -> None:
        """Test listing VM import logs from live system."""
        logs = live_client.vm_import_logs.list()

        # Should return a list (may be empty)
        assert isinstance(logs, list)

        # Each item should be a VmImportLog object
        for log in logs:
            assert hasattr(log, "level")
            assert hasattr(log, "text")
            assert hasattr(log, "timestamp")

    def test_list_vm_import_logs_by_level(self, live_client: VergeClient) -> None:
        """Test filtering VM import logs by level."""
        # Get all logs
        all_logs = live_client.vm_import_logs.list()

        # Filter by message level
        message_logs = live_client.vm_import_logs.list(level="message")

        # Each should have message level
        for log in message_logs:
            assert log.level == "message"

        # Should be fewer or equal to total
        assert len(message_logs) <= len(all_logs)

    def test_list_vm_import_logs_for_specific_import(self, live_client: VergeClient) -> None:
        """Test filtering logs for a specific import."""
        imports = live_client.vm_imports.list(limit=1)
        if not imports:
            pytest.skip("No VM imports available")

        imp = imports[0]

        # Get logs using the manager
        logs = live_client.vm_import_logs.list(vm_import=imp.key)

        # All logs should belong to this import
        for log in logs:
            assert log.vm_import == imp.key

    def test_vm_import_log_properties(self, live_client: VergeClient) -> None:
        """Test VM import log property accessors on live data."""
        logs = live_client.vm_import_logs.list(limit=1)
        if not logs:
            pytest.skip("No VM import logs available")

        log = logs[0]

        # Basic properties should be accessible
        assert isinstance(log.level, str)
        assert log.level in ["audit", "message", "warning", "error", "critical", "summary", "debug"]
        assert isinstance(log.text, str)
        assert isinstance(log.is_error, bool)
        assert isinstance(log.is_warning, bool)
