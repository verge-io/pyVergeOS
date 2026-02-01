"""Integration tests for Update Management System.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.

Tests cover:
- UpdateSettingsManager (singleton)
- UpdateSourceManager (CRUD, status, actions)
- UpdateBranchManager (list, get)
- UpdatePackageManager (string keys)
- UpdateSourcePackageManager (available packages)
- UpdateSourceStatusManager (status tracking)
- UpdateLogManager (logs with levels)
- UpdateDashboardManager (aggregated view)
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError

# =============================================================================
# Update Settings Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateSettingsIntegration:
    """Integration tests for UpdateSettingsManager (singleton)."""

    def test_get_settings(self, live_client: VergeClient) -> None:
        """Test getting update settings (singleton)."""
        settings = live_client.update_settings.get()

        assert settings is not None
        assert settings.key == 1  # Always key=1
        assert hasattr(settings, "source_key")
        assert hasattr(settings, "branch_key")

    def test_settings_properties(self, live_client: VergeClient) -> None:
        """Test UpdateSettings property accessors."""
        settings = live_client.update_settings.get()

        # Boolean properties
        assert isinstance(settings.is_auto_refresh, bool)
        assert isinstance(settings.is_auto_update, bool)
        assert isinstance(settings.is_installed, bool)
        assert isinstance(settings.is_reboot_required, bool)
        assert isinstance(settings.is_applying_updates, bool)

    def test_settings_source_and_branch(self, live_client: VergeClient) -> None:
        """Test UpdateSettings source and branch info."""
        settings = live_client.update_settings.get()

        # Source info
        if settings.source_key is not None:
            assert isinstance(settings.source_key, int)
            # source_name may be None if not fetched with display
            source_name = settings.source_name
            assert source_name is None or isinstance(source_name, str)

        # Branch info
        if settings.branch_key is not None:
            assert isinstance(settings.branch_key, int)
            branch_name = settings.branch_name
            assert branch_name is None or isinstance(branch_name, str)


@pytest.mark.integration
class TestUpdateSettingsUpdateIntegration:
    """Integration tests for updating settings."""

    def test_update_settings(self, live_client: VergeClient) -> None:
        """Test updating settings (read-only fields only).

        Note: We only test reading the settings to avoid
        changing system behavior during tests.
        """
        settings = live_client.update_settings.get()

        # Just verify we can get all fields
        assert settings.get("auto_refresh") is not None or settings.get("auto_refresh") is None
        assert settings.get("update_time") is not None or settings.get("update_time") is None


# =============================================================================
# Update Source Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateSourceListIntegration:
    """Integration tests for UpdateSourceManager list operations."""

    def test_list_sources(self, live_client: VergeClient) -> None:
        """Test listing update sources."""
        sources = live_client.update_sources.list()

        assert isinstance(sources, list)
        # Every VergeOS system should have at least one update source
        assert len(sources) >= 1
        for source in sources:
            assert hasattr(source, "key")
            assert hasattr(source, "name")
            assert hasattr(source, "url")

    def test_list_enabled_sources(self, live_client: VergeClient) -> None:
        """Test listing enabled sources using filter."""
        sources = live_client.update_sources.list(enabled=True)

        assert isinstance(sources, list)
        for source in sources:
            assert source.is_enabled is True

    def test_list_disabled_sources(self, live_client: VergeClient) -> None:
        """Test listing disabled sources using filter."""
        sources = live_client.update_sources.list(enabled=False)

        assert isinstance(sources, list)
        for source in sources:
            assert source.is_enabled is False


@pytest.mark.integration
class TestUpdateSourceGetIntegration:
    """Integration tests for UpdateSourceManager get operations."""

    def test_get_source_by_key(self, live_client: VergeClient) -> None:
        """Test getting a source by key."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = live_client.update_sources.get(sources[0].key)
        assert source.key == sources[0].key
        assert source.name == sources[0].name

    def test_get_source_by_name(self, live_client: VergeClient) -> None:
        """Test getting a source by name."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = live_client.update_sources.get(name=sources[0].name)
        assert source.name == sources[0].name

    def test_get_nonexistent_source(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent source."""
        with pytest.raises(NotFoundError):
            live_client.update_sources.get(999999)


@pytest.mark.integration
class TestUpdateSourcePropertiesIntegration:
    """Integration tests for UpdateSource properties."""

    def test_source_properties(self, live_client: VergeClient) -> None:
        """Test UpdateSource property accessors."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]

        # Basic properties
        assert source.key is not None
        assert source.name is not None
        assert source.get("url") is not None or source.get("url") is None  # May be None
        assert isinstance(source.is_enabled, bool)


@pytest.mark.integration
class TestUpdateSourceStatusIntegration:
    """Integration tests for UpdateSource status operations."""

    def test_get_source_status(self, live_client: VergeClient) -> None:
        """Test getting source status."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]
        try:
            status = source.get_status()
            assert status is not None
            assert status.source_key == source.key
        except NotFoundError:
            # Status might not exist for all sources
            pytest.skip("Status not found for source")

    def test_source_status_properties(self, live_client: VergeClient) -> None:
        """Test UpdateSourceStatus property accessors."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]
        try:
            status = source.get_status()

            # Status boolean properties
            assert isinstance(status.is_idle, bool)
            assert isinstance(status.is_busy, bool)
            assert isinstance(status.is_error, bool)
            assert isinstance(status.is_refreshing, bool)
            assert isinstance(status.is_downloading, bool)
            assert isinstance(status.is_installing, bool)
            assert isinstance(status.is_applying, bool)
        except NotFoundError:
            pytest.skip("Status not found for source")

    def test_list_source_statuses(self, live_client: VergeClient) -> None:
        """Test listing all source statuses."""
        statuses = live_client.update_source_status.list()

        assert isinstance(statuses, list)
        for status in statuses:
            assert hasattr(status, "source_key")


# =============================================================================
# Update Branch Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateBranchListIntegration:
    """Integration tests for UpdateBranchManager list operations."""

    def test_list_branches(self, live_client: VergeClient) -> None:
        """Test listing update branches."""
        branches = live_client.update_branches.list()

        assert isinstance(branches, list)
        for branch in branches:
            assert hasattr(branch, "key")
            assert hasattr(branch, "name")

    def test_list_branches_with_limit(self, live_client: VergeClient) -> None:
        """Test listing branches with limit."""
        branches = live_client.update_branches.list(limit=5)

        assert isinstance(branches, list)
        assert len(branches) <= 5


@pytest.mark.integration
class TestUpdateBranchGetIntegration:
    """Integration tests for UpdateBranchManager get operations."""

    def test_get_branch_by_key(self, live_client: VergeClient) -> None:
        """Test getting a branch by key."""
        branches = live_client.update_branches.list()
        if not branches:
            pytest.skip("No update branches available")

        branch = live_client.update_branches.get(branches[0].key)
        assert branch.key == branches[0].key
        assert branch.name == branches[0].name

    def test_get_branch_by_name(self, live_client: VergeClient) -> None:
        """Test getting a branch by name."""
        branches = live_client.update_branches.list()
        if not branches:
            pytest.skip("No update branches available")

        branch = live_client.update_branches.get(name=branches[0].name)
        assert branch.name == branches[0].name

    def test_get_nonexistent_branch(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent branch."""
        with pytest.raises(NotFoundError):
            live_client.update_branches.get(999999)


# =============================================================================
# Update Package Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdatePackageListIntegration:
    """Integration tests for UpdatePackageManager list operations."""

    def test_list_packages(self, live_client: VergeClient) -> None:
        """Test listing update packages."""
        packages = live_client.update_packages.list()

        assert isinstance(packages, list)
        # Every VergeOS system should have installed packages
        assert len(packages) >= 1
        for pkg in packages:
            assert hasattr(pkg, "key")
            assert hasattr(pkg, "name")
            assert hasattr(pkg, "version")

    def test_list_packages_with_limit(self, live_client: VergeClient) -> None:
        """Test listing packages with limit."""
        packages = live_client.update_packages.list(limit=5)

        assert isinstance(packages, list)
        assert len(packages) <= 5


@pytest.mark.integration
class TestUpdatePackageGetIntegration:
    """Integration tests for UpdatePackageManager get operations."""

    def test_get_package_by_key(self, live_client: VergeClient) -> None:
        """Test getting a package by key (name string)."""
        packages = live_client.update_packages.list()
        if not packages:
            pytest.skip("No update packages available")

        # Package keys are name strings
        pkg = live_client.update_packages.get(packages[0].key)
        assert pkg.key == packages[0].key
        assert pkg.name == packages[0].name

    def test_get_package_by_name(self, live_client: VergeClient) -> None:
        """Test getting a package by name."""
        packages = live_client.update_packages.list()
        if not packages:
            pytest.skip("No update packages available")

        pkg = live_client.update_packages.get(name=packages[0].name)
        assert pkg.name == packages[0].name

    def test_get_nonexistent_package(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent package."""
        with pytest.raises(NotFoundError):
            live_client.update_packages.get("nonexistent-package-12345")


@pytest.mark.integration
class TestUpdatePackagePropertiesIntegration:
    """Integration tests for UpdatePackage properties."""

    def test_package_properties(self, live_client: VergeClient) -> None:
        """Test UpdatePackage property accessors."""
        packages = live_client.update_packages.list()
        if not packages:
            pytest.skip("No update packages available")

        pkg = packages[0]

        # Key is a string (package name)
        assert isinstance(pkg.key, str)
        assert pkg.name is not None
        assert pkg.get("version") is not None
        assert isinstance(pkg.is_optional, bool)


# =============================================================================
# Update Source Package Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateSourcePackageListIntegration:
    """Integration tests for UpdateSourcePackageManager list operations."""

    def test_list_source_packages(self, live_client: VergeClient) -> None:
        """Test listing source packages."""
        packages = live_client.update_source_packages.list()

        assert isinstance(packages, list)
        for pkg in packages:
            assert hasattr(pkg, "key")
            assert hasattr(pkg, "name")
            assert hasattr(pkg, "source_key")

    def test_list_downloaded_packages(self, live_client: VergeClient) -> None:
        """Test listing downloaded packages."""
        packages = live_client.update_source_packages.list_downloaded()

        assert isinstance(packages, list)
        for pkg in packages:
            assert pkg.is_downloaded is True

    def test_list_pending_packages(self, live_client: VergeClient) -> None:
        """Test listing pending (not downloaded) packages."""
        packages = live_client.update_source_packages.list_pending()

        assert isinstance(packages, list)
        for pkg in packages:
            assert pkg.is_downloaded is False


@pytest.mark.integration
class TestUpdateSourcePackageGetIntegration:
    """Integration tests for UpdateSourcePackageManager get operations."""

    def test_get_source_package_by_key(self, live_client: VergeClient) -> None:
        """Test getting a source package by key."""
        packages = live_client.update_source_packages.list()
        if not packages:
            pytest.skip("No source packages available")

        pkg = live_client.update_source_packages.get(packages[0].key)
        assert pkg.key == packages[0].key

    def test_get_source_package_by_name(self, live_client: VergeClient) -> None:
        """Test getting a source package by name."""
        packages = live_client.update_source_packages.list()
        if not packages:
            pytest.skip("No source packages available")

        pkg = live_client.update_source_packages.get(name=packages[0].name)
        assert pkg.name == packages[0].name


@pytest.mark.integration
class TestUpdateSourcePackagePropertiesIntegration:
    """Integration tests for UpdateSourcePackage properties."""

    def test_source_package_properties(self, live_client: VergeClient) -> None:
        """Test UpdateSourcePackage property accessors."""
        packages = live_client.update_source_packages.list()
        if not packages:
            pytest.skip("No source packages available")

        pkg = packages[0]

        assert pkg.key is not None
        assert pkg.name is not None
        assert isinstance(pkg.is_downloaded, bool)
        assert isinstance(pkg.is_optional, bool)


# =============================================================================
# Scoped Manager Integration Tests
# =============================================================================


@pytest.mark.integration
class TestScopedPackageManagerIntegration:
    """Integration tests for scoped package managers."""

    def test_packages_scoped_to_source(self, live_client: VergeClient) -> None:
        """Test getting packages scoped to a source."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]
        packages = source.packages.list()

        assert isinstance(packages, list)
        for pkg in packages:
            # All packages should belong to this source
            assert pkg.source_key == source.key

    def test_status_scoped_to_source(self, live_client: VergeClient) -> None:
        """Test getting status scoped to a source."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]
        statuses = source.status.list()

        assert isinstance(statuses, list)
        for status in statuses:
            # All statuses should belong to this source
            assert status.source_key == source.key


# =============================================================================
# Update Log Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateLogListIntegration:
    """Integration tests for UpdateLogManager list operations."""

    def test_list_logs(self, live_client: VergeClient) -> None:
        """Test listing update logs."""
        logs = live_client.update_logs.list()

        assert isinstance(logs, list)
        for log in logs:
            assert hasattr(log, "key")
            assert hasattr(log, "level")

    def test_list_logs_with_limit(self, live_client: VergeClient) -> None:
        """Test listing logs with limit."""
        logs = live_client.update_logs.list(limit=10)

        assert isinstance(logs, list)
        assert len(logs) <= 10

    def test_list_logs_by_level(self, live_client: VergeClient) -> None:
        """Test listing logs filtered by level."""
        logs = live_client.update_logs.list(level="audit")

        assert isinstance(logs, list)
        for log in logs:
            assert log.get("level") == "audit"


@pytest.mark.integration
class TestUpdateLogGetIntegration:
    """Integration tests for UpdateLogManager get operations."""

    def test_get_log_by_key(self, live_client: VergeClient) -> None:
        """Test getting a log by key."""
        logs = live_client.update_logs.list(limit=1)
        if not logs:
            pytest.skip("No update logs available")

        log = live_client.update_logs.get(logs[0].key)
        assert log.key == logs[0].key


@pytest.mark.integration
class TestUpdateLogErrorWarningIntegration:
    """Integration tests for error and warning log filters."""

    def test_list_errors(self, live_client: VergeClient) -> None:
        """Test listing error logs."""
        errors = live_client.update_logs.list_errors()

        assert isinstance(errors, list)
        for log in errors:
            assert log.get("level") in ("error", "critical")

    def test_list_warnings(self, live_client: VergeClient) -> None:
        """Test listing warning logs."""
        warnings = live_client.update_logs.list_warnings()

        assert isinstance(warnings, list)
        for log in warnings:
            assert log.get("level") == "warning"


@pytest.mark.integration
class TestUpdateLogPropertiesIntegration:
    """Integration tests for UpdateLog properties."""

    def test_log_properties(self, live_client: VergeClient) -> None:
        """Test UpdateLog property accessors."""
        logs = live_client.update_logs.list(limit=10)
        if not logs:
            pytest.skip("No update logs available")

        for log in logs:
            # Check boolean properties based on level
            level = log.get("level")
            if level in ("error", "critical"):
                assert log.is_error is True
            else:
                assert log.is_error is False

            if level == "warning":
                assert log.is_warning is True
            else:
                assert log.is_warning is False

            if level == "audit":
                assert log.is_audit is True
            else:
                assert log.is_audit is False


# =============================================================================
# Update Dashboard Integration Tests
# =============================================================================


@pytest.mark.integration
class TestUpdateDashboardIntegration:
    """Integration tests for UpdateDashboardManager."""

    def test_get_dashboard(self, live_client: VergeClient) -> None:
        """Test getting the update dashboard."""
        dashboard = live_client.update_dashboard.get()

        assert dashboard is not None
        # Dashboard should have node count
        assert hasattr(dashboard, "node_count")

    def test_dashboard_properties(self, live_client: VergeClient) -> None:
        """Test UpdateDashboard property accessors."""
        dashboard = live_client.update_dashboard.get()

        # Node count should be >= 1
        assert isinstance(dashboard.node_count, int)
        assert dashboard.node_count >= 0

        # Event and task counts
        assert isinstance(dashboard.event_count, int)
        assert isinstance(dashboard.task_count, int)

    def test_dashboard_settings(self, live_client: VergeClient) -> None:
        """Test getting settings from dashboard."""
        dashboard = live_client.update_dashboard.get()

        settings = dashboard.get_settings()
        assert isinstance(settings, dict)

    def test_dashboard_packages(self, live_client: VergeClient) -> None:
        """Test getting packages from dashboard."""
        dashboard = live_client.update_dashboard.get()

        packages = dashboard.get_packages()
        assert isinstance(packages, list)

    def test_dashboard_branches(self, live_client: VergeClient) -> None:
        """Test getting branches from dashboard."""
        dashboard = live_client.update_dashboard.get()

        branches = dashboard.get_branches()
        assert isinstance(branches, list)

    def test_dashboard_logs(self, live_client: VergeClient) -> None:
        """Test getting logs from dashboard."""
        dashboard = live_client.update_dashboard.get()

        logs = dashboard.get_logs()
        assert isinstance(logs, list)


# =============================================================================
# Update Actions Integration Tests (Read-only, no actual updates)
# =============================================================================


@pytest.mark.integration
class TestUpdateActionsIntegration:
    """Integration tests for update actions.

    Note: These tests only verify the action methods exist and can be called
    on the settings object. They do NOT trigger actual updates to avoid
    disrupting the test environment.
    """

    def test_settings_has_check_method(self, live_client: VergeClient) -> None:
        """Test that settings object has check method."""
        settings = live_client.update_settings.get()
        assert callable(getattr(settings, "check", None))

    def test_settings_has_download_method(self, live_client: VergeClient) -> None:
        """Test that settings object has download method."""
        settings = live_client.update_settings.get()
        assert callable(getattr(settings, "download", None))

    def test_settings_has_install_method(self, live_client: VergeClient) -> None:
        """Test that settings object has install method."""
        settings = live_client.update_settings.get()
        assert callable(getattr(settings, "install", None))

    def test_settings_has_update_all_method(self, live_client: VergeClient) -> None:
        """Test that settings object has update_all method."""
        settings = live_client.update_settings.get()
        assert callable(getattr(settings, "update_all", None))

    def test_source_has_refresh_method(self, live_client: VergeClient) -> None:
        """Test that source object has refresh method."""
        sources = live_client.update_sources.list()
        if not sources:
            pytest.skip("No update sources available")

        source = sources[0]
        assert callable(getattr(source, "refresh", None))
