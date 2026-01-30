"""Integration tests for Catalog Management System.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.

Tests cover:
- CatalogRepositoryManager
- CatalogManager
- CatalogRepositoryLogManager
- CatalogLogManager
- Scoped managers (repo.catalogs, repo.logs, catalog.logs)
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError

# =============================================================================
# Catalog Repository Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogRepositoryListIntegration:
    """Integration tests for CatalogRepositoryManager list operations."""

    def test_list_repositories(self, live_client: VergeClient) -> None:
        """Test listing catalog repositories from live system."""
        repos = live_client.catalog_repositories.list()

        assert isinstance(repos, list)
        # Every VergeOS system should have at least the Local repository
        assert len(repos) >= 1
        for repo in repos:
            assert hasattr(repo, "key")
            assert hasattr(repo, "name")
            assert hasattr(repo, "repository_type")

    def test_list_enabled_repositories(self, live_client: VergeClient) -> None:
        """Test listing enabled repositories using filter."""
        repos = live_client.catalog_repositories.list(enabled=True)

        assert isinstance(repos, list)
        for repo in repos:
            assert repo.is_enabled is True

    def test_list_disabled_repositories(self, live_client: VergeClient) -> None:
        """Test listing disabled repositories using filter."""
        repos = live_client.catalog_repositories.list(enabled=False)

        assert isinstance(repos, list)
        for repo in repos:
            assert repo.is_enabled is False

    def test_list_by_type(self, live_client: VergeClient) -> None:
        """Test listing repositories by type using filter."""
        # Local repository should always exist
        repos = live_client.catalog_repositories.list(type="local")

        assert isinstance(repos, list)
        for repo in repos:
            assert repo.repository_type == "local"


@pytest.mark.integration
class TestCatalogRepositoryGetIntegration:
    """Integration tests for CatalogRepositoryManager get operations."""

    def test_get_repository_by_key(self, live_client: VergeClient) -> None:
        """Test getting a repository by key."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = live_client.catalog_repositories.get(repos[0].key)
        assert repo.key == repos[0].key
        assert repo.name == repos[0].name

    def test_get_repository_by_name(self, live_client: VergeClient) -> None:
        """Test getting a repository by name."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = live_client.catalog_repositories.get(name=repos[0].name)
        assert repo.name == repos[0].name

    def test_get_local_repository(self, live_client: VergeClient) -> None:
        """Test getting the Local repository by name."""
        # Every VergeOS system should have a Local repository
        try:
            repo = live_client.catalog_repositories.get(name="Local")
            assert repo.name == "Local"
            assert repo.repository_type == "local"
        except NotFoundError:
            pytest.skip("Local repository not found")

    def test_get_nonexistent_repository(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent repository."""
        with pytest.raises(NotFoundError):
            live_client.catalog_repositories.get(999999)


@pytest.mark.integration
class TestCatalogRepositoryPropertiesIntegration:
    """Integration tests for CatalogRepository properties."""

    def test_repository_properties(self, live_client: VergeClient) -> None:
        """Test CatalogRepository property accessors."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = repos[0]

        # Basic properties
        assert repo.key is not None
        assert repo.name is not None
        assert repo.repository_type is not None
        assert isinstance(repo.is_enabled, bool)

    def test_repository_type_checks(self, live_client: VergeClient) -> None:
        """Test repository type checking properties."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        for repo in repos:
            # is_local should be True only for local type
            if repo.repository_type == "local":
                assert repo.is_local is True
                assert repo.is_remote is False
            else:
                assert repo.is_local is False
                # is_remote should be True for remote types
                if repo.repository_type in ("remote", "remote-git", "yottabyte"):
                    assert repo.is_remote is True


@pytest.mark.integration
class TestCatalogRepositoryStatusIntegration:
    """Integration tests for CatalogRepositoryStatus operations."""

    def test_get_repository_status(self, live_client: VergeClient) -> None:
        """Test getting repository status."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = repos[0]
        status = repo.get_status()

        assert status is not None
        assert hasattr(status, "repository_key")
        assert status.repository_key == repo.key

    def test_repository_status_properties(self, live_client: VergeClient) -> None:
        """Test CatalogRepositoryStatus property accessors."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = repos[0]
        status = repo.get_status()

        # Status boolean properties
        assert isinstance(status.is_online, bool)
        assert isinstance(status.is_error, bool)
        assert isinstance(status.is_busy, bool)

    def test_list_statuses(self, live_client: VergeClient) -> None:
        """Test listing all repository statuses."""
        statuses = live_client.catalog_repository_status.list()

        assert isinstance(statuses, list)
        for status in statuses:
            assert hasattr(status, "repository_key")


# =============================================================================
# Catalog Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogListIntegration:
    """Integration tests for CatalogManager list operations."""

    def test_list_catalogs(self, live_client: VergeClient) -> None:
        """Test listing catalogs from live system."""
        catalogs = live_client.catalogs.list()

        assert isinstance(catalogs, list)
        for catalog in catalogs:
            assert hasattr(catalog, "key")
            assert hasattr(catalog, "name")
            assert hasattr(catalog, "repository_key")

    def test_list_enabled_catalogs(self, live_client: VergeClient) -> None:
        """Test listing enabled catalogs using filter."""
        catalogs = live_client.catalogs.list(enabled=True)

        assert isinstance(catalogs, list)
        for catalog in catalogs:
            assert catalog.is_enabled is True

    def test_list_disabled_catalogs(self, live_client: VergeClient) -> None:
        """Test listing disabled catalogs using filter."""
        catalogs = live_client.catalogs.list(enabled=False)

        assert isinstance(catalogs, list)
        for catalog in catalogs:
            assert catalog.is_enabled is False


@pytest.mark.integration
class TestCatalogGetIntegration:
    """Integration tests for CatalogManager get operations."""

    def test_get_catalog_by_key(self, live_client: VergeClient) -> None:
        """Test getting a catalog by key."""
        catalogs = live_client.catalogs.list()
        if not catalogs:
            pytest.skip("No catalogs available")

        catalog = live_client.catalogs.get(catalogs[0].key)
        assert catalog.key == catalogs[0].key
        assert catalog.name == catalogs[0].name

    def test_get_catalog_by_name(self, live_client: VergeClient) -> None:
        """Test getting a catalog by name."""
        catalogs = live_client.catalogs.list()
        if not catalogs:
            pytest.skip("No catalogs available")

        catalog = live_client.catalogs.get(name=catalogs[0].name)
        assert catalog.name == catalogs[0].name

    def test_get_nonexistent_catalog(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent catalog."""
        with pytest.raises(NotFoundError):
            live_client.catalogs.get("nonexistent-key-12345")


@pytest.mark.integration
class TestCatalogPropertiesIntegration:
    """Integration tests for Catalog properties."""

    def test_catalog_properties(self, live_client: VergeClient) -> None:
        """Test Catalog property accessors."""
        catalogs = live_client.catalogs.list()
        if not catalogs:
            pytest.skip("No catalogs available")

        catalog = catalogs[0]

        # Basic properties
        assert catalog.key is not None
        assert catalog.name is not None
        assert catalog.repository_key is not None
        assert isinstance(catalog.is_enabled, bool)

    def test_catalog_scope(self, live_client: VergeClient) -> None:
        """Test Catalog scope property."""
        catalogs = live_client.catalogs.list()
        if not catalogs:
            pytest.skip("No catalogs available")

        for catalog in catalogs:
            scope = catalog.scope
            # Scope should be one of the valid values
            assert scope in ("private", "public", None) or isinstance(scope, str)


# =============================================================================
# Scoped Manager Integration Tests
# =============================================================================


@pytest.mark.integration
class TestScopedCatalogManagerIntegration:
    """Integration tests for scoped catalog managers."""

    def test_catalogs_scoped_to_repository(self, live_client: VergeClient) -> None:
        """Test getting catalogs scoped to a repository."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        for repo in repos:
            catalogs = repo.catalogs.list()

            assert isinstance(catalogs, list)
            for catalog in catalogs:
                # All catalogs should belong to this repository
                assert catalog.repository_key == repo.key

    def test_repository_catalogs_manager_methods(self, live_client: VergeClient) -> None:
        """Test ScopedCatalogManager methods."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = repos[0]

        # Test list with enabled filter
        enabled = repo.catalogs.list(enabled=True)
        assert isinstance(enabled, list)
        for cat in enabled:
            assert cat.is_enabled is True
            assert cat.repository_key == repo.key

        # Test list with disabled filter
        disabled = repo.catalogs.list(enabled=False)
        assert isinstance(disabled, list)
        for cat in disabled:
            assert cat.is_enabled is False
            assert cat.repository_key == repo.key


# =============================================================================
# Catalog Repository Log Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogRepositoryLogIntegration:
    """Integration tests for CatalogRepositoryLogManager operations."""

    def test_list_repository_logs(self, live_client: VergeClient) -> None:
        """Test listing catalog repository logs."""
        logs = live_client.catalog_repository_logs.list()

        assert isinstance(logs, list)
        for log in logs:
            assert hasattr(log, "key")
            assert hasattr(log, "repository_key")

    def test_list_errors(self, live_client: VergeClient) -> None:
        """Test listing error logs."""
        errors = live_client.catalog_repository_logs.list_errors()

        assert isinstance(errors, list)
        for log in errors:
            assert log.get("level") == "error"

    def test_list_warnings(self, live_client: VergeClient) -> None:
        """Test listing warning logs."""
        warnings = live_client.catalog_repository_logs.list_warnings()

        assert isinstance(warnings, list)
        for log in warnings:
            assert log.get("level") == "warning"


@pytest.mark.integration
class TestScopedRepositoryLogManagerIntegration:
    """Integration tests for scoped repository log managers."""

    def test_logs_scoped_to_repository(self, live_client: VergeClient) -> None:
        """Test getting logs scoped to a repository."""
        repos = live_client.catalog_repositories.list()
        if not repos:
            pytest.skip("No repositories available")

        repo = repos[0]
        logs = repo.logs.list()

        assert isinstance(logs, list)
        for log in logs:
            # All logs should belong to this repository
            assert log.repository_key == repo.key


# =============================================================================
# Catalog Log Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogLogIntegration:
    """Integration tests for CatalogLogManager operations."""

    def test_list_catalog_logs(self, live_client: VergeClient) -> None:
        """Test listing catalog logs."""
        logs = live_client.catalog_logs.list()

        assert isinstance(logs, list)
        for log in logs:
            assert hasattr(log, "key")
            assert hasattr(log, "catalog_key")

    def test_list_errors(self, live_client: VergeClient) -> None:
        """Test listing error logs."""
        errors = live_client.catalog_logs.list_errors()

        assert isinstance(errors, list)
        for log in errors:
            assert log.get("level") == "error"


@pytest.mark.integration
class TestScopedCatalogLogManagerIntegration:
    """Integration tests for scoped catalog log managers."""

    def test_logs_scoped_to_catalog(self, live_client: VergeClient) -> None:
        """Test getting logs scoped to a catalog."""
        catalogs = live_client.catalogs.list()
        if not catalogs:
            pytest.skip("No catalogs available")

        catalog = catalogs[0]
        logs = catalog.logs.list()

        assert isinstance(logs, list)
        for log in logs:
            # All logs should belong to this catalog
            assert log.catalog_key == catalog.key


# =============================================================================
# Catalog CRUD Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogCRUDIntegration:
    """Integration tests for Catalog CRUD operations."""

    def test_create_update_delete_catalog(self, live_client: VergeClient) -> None:
        """Test creating, updating, and deleting a catalog in Local repository."""
        # Get the local repository
        try:
            local_repo = live_client.catalog_repositories.get(name="Local")
        except NotFoundError:
            pytest.skip("Local repository not found")

        # Create
        catalog = live_client.catalogs.create(
            name="PyVergeOS Test Catalog",
            repository=local_repo.key,
            description="Integration test catalog",
            enabled=True,
        )

        try:
            assert catalog.name == "PyVergeOS Test Catalog"
            assert catalog.repository_key == local_repo.key
            assert catalog.get("description") == "Integration test catalog"

            # Update
            updated = live_client.catalogs.update(
                catalog.key,
                description="Updated description",
            )
            assert updated.get("description") == "Updated description"

        finally:
            # Delete
            live_client.catalogs.delete(catalog.key)

            # Verify deleted
            with pytest.raises(NotFoundError):
                live_client.catalogs.get(catalog.key)


# =============================================================================
# Repository Refresh Integration Tests
# =============================================================================


@pytest.mark.integration
class TestCatalogRepositoryRefreshIntegration:
    """Integration tests for repository refresh operations."""

    def test_refresh_repository(self, live_client: VergeClient) -> None:
        """Test refreshing a remote repository.

        Note: This test only verifies the API call succeeds.
        It does not wait for the refresh to complete.
        """
        # Find a remote repository
        repos = live_client.catalog_repositories.list()
        remote_repos = [r for r in repos if r.is_remote]

        if not remote_repos:
            pytest.skip("No remote repositories available")

        repo = remote_repos[0]

        # Check current status
        status_before = repo.get_status()
        assert status_before is not None

        # Attempt refresh (may fail if already refreshing or offline)
        # We just verify the API call doesn't raise an unexpected error
        try:
            result = repo.refresh_catalogs()
            # Result may be None or a dict depending on API response
            assert result is None or isinstance(result, dict)
        except Exception as e:
            # Some errors are expected (e.g., already refreshing)
            # Just ensure it's not a connection error
            assert "connection" not in str(e).lower()
