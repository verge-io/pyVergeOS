"""Unit tests for catalog management resources."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.client import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.catalogs import (
    Catalog,
    CatalogLog,
    CatalogLogManager,
    CatalogManager,
    CatalogRepository,
    CatalogRepositoryLog,
    CatalogRepositoryLogManager,
    CatalogRepositoryManager,
    CatalogRepositoryStatus,
    CatalogRepositoryStatusManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client.is_connected = True
    return client


# =============================================================================
# CatalogRepositoryManager Tests
# =============================================================================


class TestCatalogRepositoryManager:
    """Tests for CatalogRepositoryManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = CatalogRepositoryManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "catalog_repositories"

    def test_list_returns_repositories(self, mock_client: MagicMock) -> None:
        """Test listing repositories."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Local", "type": "local"},
            {"$key": 2, "name": "Verge.io Recipes", "type": "yottabyte"},
        ]

        manager = CatalogRepositoryManager(mock_client)
        repos = manager.list()

        assert len(repos) == 2
        assert isinstance(repos[0], CatalogRepository)
        assert repos[0]["name"] == "Local"
        assert repos[1]["type"] == "yottabyte"

    def test_list_with_type_filter(self, mock_client: MagicMock) -> None:
        """Test listing with type filter."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Local", "type": "local"},
        ]

        manager = CatalogRepositoryManager(mock_client)
        manager.list(type="local")

        call_args = mock_client._request.call_args
        assert "type eq 'local'" in call_args[1]["params"]["filter"]

    def test_list_with_enabled_filter(self, mock_client: MagicMock) -> None:
        """Test listing with enabled filter."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryManager(mock_client)
        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq 1" in call_args[1]["params"]["filter"]

    def test_list_returns_empty_on_none(self, mock_client: MagicMock) -> None:
        """Test listing returns empty list on None response."""
        mock_client._request.return_value = None

        manager = CatalogRepositoryManager(mock_client)
        repos = manager.list()

        assert repos == []

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting repository by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Local",
            "type": "local",
        }

        manager = CatalogRepositoryManager(mock_client)
        repo = manager.get(key=1)

        assert isinstance(repo, CatalogRepository)
        assert repo.key == 1
        assert repo["name"] == "Local"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting repository by name."""
        mock_client._request.return_value = [
            {"$key": 2, "name": "Verge.io Recipes", "type": "yottabyte"},
        ]

        manager = CatalogRepositoryManager(mock_client)
        repo = manager.get(name="Verge.io Recipes")

        assert repo["name"] == "Verge.io Recipes"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = CatalogRepositoryManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_requires_identifier(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without identifier."""
        manager = CatalogRepositoryManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_create_local_repository(self, mock_client: MagicMock) -> None:
        """Test creating a local repository."""
        mock_client._request.side_effect = [
            {"$key": 3},  # POST response
            {"$key": 3, "name": "Test Repo", "type": "local"},  # GET response
        ]

        manager = CatalogRepositoryManager(mock_client)
        repo = manager.create(
            name="Test Repo",
            type="local",
            description="Test repository",
        )

        assert repo.key == 3
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "catalog_repositories")

    def test_create_remote_repository(self, mock_client: MagicMock) -> None:
        """Test creating a remote repository."""
        mock_client._request.side_effect = [
            {"$key": 3},
            {"$key": 3, "name": "Remote", "type": "remote", "url": "https://example.com"},
        ]

        manager = CatalogRepositoryManager(mock_client)
        manager.create(
            name="Remote",
            type="remote",
            url="https://example.com",
            user="apiuser",
            password="secret",  # noqa: S106
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["url"] == "https://example.com"
        assert body["user"] == "apiuser"
        assert body["password"] == "secret"

    def test_update_repository(self, mock_client: MagicMock) -> None:
        """Test updating a repository."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated", "description": "New desc"},  # GET response
        ]

        manager = CatalogRepositoryManager(mock_client)
        manager.update(key=1, description="New desc", auto_refresh=False)

        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "catalog_repositories/1")
        body = put_call[1]["json_data"]
        assert body["description"] == "New desc"
        assert body["auto_refresh"] is False

    def test_update_no_changes(self, mock_client: MagicMock) -> None:
        """Test update with no changes returns current repo."""
        mock_client._request.return_value = {"$key": 1, "name": "Local"}

        manager = CatalogRepositoryManager(mock_client)
        manager.update(key=1)

        # Should call GET, not PUT
        mock_client._request.assert_called_once()
        assert mock_client._request.call_args[0][0] == "GET"

    def test_delete_repository(self, mock_client: MagicMock) -> None:
        """Test deleting a repository."""
        mock_client._request.return_value = None

        manager = CatalogRepositoryManager(mock_client)
        manager.delete(key=2)

        mock_client._request.assert_called_with("DELETE", "catalog_repositories/2")

    def test_refresh_repository(self, mock_client: MagicMock) -> None:
        """Test refreshing a repository."""
        mock_client._request.return_value = {"task": 123}

        manager = CatalogRepositoryManager(mock_client)
        result = manager.refresh(key=1)

        mock_client._request.assert_called_once_with(
            "POST",
            "catalog_repository_actions",
            json_data={"repository": 1, "action": "refresh"},
        )
        assert result == {"task": 123}

    def test_get_status(self, mock_client: MagicMock) -> None:
        """Test getting repository status."""
        mock_client._request.return_value = [
            {"$key": 1, "repository": 1, "status": "online", "state": "online"},
        ]

        manager = CatalogRepositoryManager(mock_client)
        status = manager.get_status(key=1)

        assert isinstance(status, CatalogRepositoryStatus)
        assert status["status"] == "online"

    def test_catalogs_scope(self, mock_client: MagicMock) -> None:
        """Test getting scoped catalog manager."""
        manager = CatalogRepositoryManager(mock_client)
        catalog_mgr = manager.catalogs(key=1)

        assert isinstance(catalog_mgr, CatalogManager)
        assert catalog_mgr._repository_key == 1

    def test_logs_scope(self, mock_client: MagicMock) -> None:
        """Test getting scoped log manager."""
        manager = CatalogRepositoryManager(mock_client)
        log_mgr = manager.logs(key=1)

        assert isinstance(log_mgr, CatalogRepositoryLogManager)
        assert log_mgr._repository_key == 1


class TestCatalogRepository:
    """Tests for CatalogRepository resource object."""

    def test_properties(self, mock_client: MagicMock) -> None:
        """Test repository properties."""
        manager = CatalogRepositoryManager(mock_client)
        repo = CatalogRepository(
            {
                "$key": 1,
                "name": "Local",
                "type": "local",
                "enabled": True,
                "auto_refresh": True,
            },
            manager,
        )

        assert repo.key == 1
        assert repo.is_enabled is True
        assert repo.is_local is True
        assert repo.is_remote is False
        assert repo.repository_type == "local"

    def test_remote_repository_properties(self, mock_client: MagicMock) -> None:
        """Test remote repository properties."""
        manager = CatalogRepositoryManager(mock_client)
        repo = CatalogRepository(
            {
                "$key": 2,
                "name": "Verge.io",
                "type": "yottabyte",
                "enabled": True,
            },
            manager,
        )

        assert repo.is_local is False
        assert repo.is_remote is True

    def test_nested_managers(self, mock_client: MagicMock) -> None:
        """Test nested manager access."""
        manager = CatalogRepositoryManager(mock_client)
        repo = CatalogRepository({"$key": 1, "name": "Local"}, manager)

        assert isinstance(repo.catalogs, CatalogManager)
        assert isinstance(repo.logs, CatalogRepositoryLogManager)
        assert isinstance(repo.status, CatalogRepositoryStatusManager)

    def test_refresh_catalogs(self, mock_client: MagicMock) -> None:
        """Test refresh_catalogs method."""
        mock_client._request.return_value = {"task": 123}

        manager = CatalogRepositoryManager(mock_client)
        repo = CatalogRepository({"$key": 1, "name": "Local"}, manager)
        result = repo.refresh_catalogs()

        assert result == {"task": 123}


# =============================================================================
# CatalogManager Tests
# =============================================================================


class TestCatalogManager:
    """Tests for CatalogManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = CatalogManager(mock_client)
        assert manager._endpoint == "catalogs"
        assert manager._repository_key is None

    def test_init_with_scope(self, mock_client: MagicMock) -> None:
        """Test manager initialization with repository scope."""
        manager = CatalogManager(mock_client, repository_key=1)
        assert manager._repository_key == 1

    def test_list_returns_catalogs(self, mock_client: MagicMock) -> None:
        """Test listing catalogs."""
        mock_client._request.return_value = [
            {"$key": "abc123def456789012345678901234567890", "name": "Test Catalog"},
        ]

        manager = CatalogManager(mock_client)
        catalogs = manager.list()

        assert len(catalogs) == 1
        assert isinstance(catalogs[0], Catalog)

    def test_list_with_repository_filter(self, mock_client: MagicMock) -> None:
        """Test listing with repository filter."""
        mock_client._request.return_value = []

        manager = CatalogManager(mock_client)
        manager.list(repository=1)

        call_args = mock_client._request.call_args
        assert "repository eq 1" in call_args[1]["params"]["filter"]

    def test_list_scoped_includes_repository(self, mock_client: MagicMock) -> None:
        """Test scoped manager includes repository filter."""
        mock_client._request.return_value = []

        manager = CatalogManager(mock_client, repository_key=1)
        manager.list()

        call_args = mock_client._request.call_args
        assert "repository eq 1" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting catalog by key (40-char hex)."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.return_value = [
            {"$key": catalog_key, "name": "Test", "id": catalog_key},
        ]

        manager = CatalogManager(mock_client)
        catalog = manager.get(key=catalog_key)

        assert isinstance(catalog, Catalog)
        assert catalog.key == catalog_key

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting catalog by name."""
        mock_client._request.return_value = [
            {"$key": "abc123def456789012345678901234567890", "name": "Test Catalog"},
        ]

        manager = CatalogManager(mock_client)
        catalog = manager.get(name="Test Catalog")

        assert catalog["name"] == "Test Catalog"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError."""
        mock_client._request.return_value = []

        manager = CatalogManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key="nonexistent0000000000000000000000000")

    def test_create_catalog(self, mock_client: MagicMock) -> None:
        """Test creating a catalog."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.side_effect = [
            {"$key": catalog_key},
            [{"$key": catalog_key, "name": "New Catalog", "id": catalog_key}],
        ]

        manager = CatalogManager(mock_client)
        catalog = manager.create(
            name="New Catalog",
            repository=1,
            description="Test description",
            publishing_scope="private",
        )

        assert catalog.key == catalog_key
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["name"] == "New Catalog"
        assert body["repository"] == 1
        assert body["publishing_scope"] == "private"

    def test_update_catalog(self, mock_client: MagicMock) -> None:
        """Test updating a catalog."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": catalog_key, "name": "Updated", "id": catalog_key}],  # GET
        ]

        manager = CatalogManager(mock_client)
        manager.update(key=catalog_key, name="Updated", enabled=False)

        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", f"catalogs/{catalog_key}")

    def test_delete_catalog(self, mock_client: MagicMock) -> None:
        """Test deleting a catalog."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.return_value = None

        manager = CatalogManager(mock_client)
        manager.delete(key=catalog_key)

        mock_client._request.assert_called_with("DELETE", f"catalogs/{catalog_key}")

    def test_logs_scope(self, mock_client: MagicMock) -> None:
        """Test getting scoped log manager."""
        catalog_key = "abc123def456789012345678901234567890"
        manager = CatalogManager(mock_client)
        log_mgr = manager.logs(key=catalog_key)

        assert isinstance(log_mgr, CatalogLogManager)
        assert log_mgr._catalog_key == catalog_key


class TestCatalog:
    """Tests for Catalog resource object."""

    def test_string_key(self, mock_client: MagicMock) -> None:
        """Test catalog uses string key."""
        catalog_key = "abc123def456789012345678901234567890"
        manager = CatalogManager(mock_client)
        catalog = Catalog({"$key": catalog_key, "id": catalog_key}, manager)

        assert catalog.key == catalog_key
        assert isinstance(catalog.key, str)

    def test_properties(self, mock_client: MagicMock) -> None:
        """Test catalog properties."""
        manager = CatalogManager(mock_client)
        catalog = Catalog(
            {
                "$key": "abc123def456789012345678901234567890",
                "repository": 1,
                "publishing_scope": "global",
                "enabled": True,
            },
            manager,
        )

        assert catalog.repository_key == 1
        assert catalog.scope == "global"
        assert catalog.is_enabled is True

    def test_nested_logs_manager(self, mock_client: MagicMock) -> None:
        """Test nested logs manager."""
        catalog_key = "abc123def456789012345678901234567890"
        manager = CatalogManager(mock_client)
        catalog = Catalog({"$key": catalog_key}, manager)

        assert isinstance(catalog.logs, CatalogLogManager)
        assert catalog.logs._catalog_key == catalog_key

    def test_refresh(self, mock_client: MagicMock) -> None:
        """Test refresh method."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.return_value = [
            {"$key": catalog_key, "name": "Refreshed", "id": catalog_key},
        ]

        manager = CatalogManager(mock_client)
        catalog = Catalog({"$key": catalog_key}, manager)
        refreshed = catalog.refresh()

        assert refreshed["name"] == "Refreshed"

    def test_save(self, mock_client: MagicMock) -> None:
        """Test save method."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": catalog_key, "name": "Saved", "id": catalog_key}],  # GET
        ]

        manager = CatalogManager(mock_client)
        catalog = Catalog({"$key": catalog_key, "name": "Original"}, manager)
        saved = catalog.save(name="Saved")

        assert saved["name"] == "Saved"

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test delete method."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.return_value = None

        manager = CatalogManager(mock_client)
        catalog = Catalog({"$key": catalog_key}, manager)
        catalog.delete()

        mock_client._request.assert_called_with("DELETE", f"catalogs/{catalog_key}")


# =============================================================================
# CatalogRepositoryStatusManager Tests
# =============================================================================


class TestCatalogRepositoryStatusManager:
    """Tests for CatalogRepositoryStatusManager."""

    def test_list(self, mock_client: MagicMock) -> None:
        """Test listing statuses."""
        mock_client._request.return_value = [
            {"$key": 1, "repository": 1, "status": "online", "state": "online"},
        ]

        manager = CatalogRepositoryStatusManager(mock_client)
        statuses = manager.list()

        assert len(statuses) == 1
        assert isinstance(statuses[0], CatalogRepositoryStatus)

    def test_list_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager includes filter."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryStatusManager(mock_client, repository_key=1)
        manager.list()

        call_args = mock_client._request.call_args
        assert "repository eq 1" in call_args[1]["params"]["filter"]

    def test_get_for_repository(self, mock_client: MagicMock) -> None:
        """Test get_for_repository method."""
        mock_client._request.return_value = [
            {"$key": 1, "repository": 1, "status": "online"},
        ]

        manager = CatalogRepositoryStatusManager(mock_client)
        status = manager.get_for_repository(repository_key=1)

        assert status["repository"] == 1


class TestCatalogRepositoryStatus:
    """Tests for CatalogRepositoryStatus resource object."""

    def test_properties(self, mock_client: MagicMock) -> None:
        """Test status properties."""
        manager = CatalogRepositoryStatusManager(mock_client)
        status = CatalogRepositoryStatus(
            {
                "$key": 1,
                "repository": 1,
                "status": "online",
                "state": "online",
            },
            manager,
        )

        assert status.repository_key == 1
        assert status.is_online is True
        assert status.is_error is False
        assert status.is_busy is False

    def test_busy_states(self, mock_client: MagicMock) -> None:
        """Test busy state detection."""
        manager = CatalogRepositoryStatusManager(mock_client)

        for busy_status in ["refreshing", "downloading", "installing", "applying"]:
            status = CatalogRepositoryStatus({"status": busy_status}, manager)
            assert status.is_busy is True

    def test_error_state(self, mock_client: MagicMock) -> None:
        """Test error state detection."""
        manager = CatalogRepositoryStatusManager(mock_client)
        status = CatalogRepositoryStatus({"state": "error"}, manager)

        assert status.is_error is True
        assert status.is_online is False


# =============================================================================
# Log Manager Tests
# =============================================================================


class TestCatalogRepositoryLogManager:
    """Tests for CatalogRepositoryLogManager."""

    def test_list(self, mock_client: MagicMock) -> None:
        """Test listing logs."""
        mock_client._request.return_value = [
            {"$key": 1, "level": "message", "text": "Test log"},
        ]

        manager = CatalogRepositoryLogManager(mock_client)
        logs = manager.list()

        assert len(logs) == 1
        assert isinstance(logs[0], CatalogRepositoryLog)

    def test_list_with_level_filter(self, mock_client: MagicMock) -> None:
        """Test listing with level filter."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryLogManager(mock_client)
        manager.list(level="error")

        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager includes filter."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryLogManager(mock_client, repository_key=1)
        manager.list()

        call_args = mock_client._request.call_args
        assert "catalog_repository eq 1" in call_args[1]["params"]["filter"]

    def test_list_errors(self, mock_client: MagicMock) -> None:
        """Test list_errors convenience method."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryLogManager(mock_client)
        manager.list_errors()

        call_args = mock_client._request.call_args
        assert "error" in call_args[1]["params"]["filter"]
        assert "critical" in call_args[1]["params"]["filter"]

    def test_list_warnings(self, mock_client: MagicMock) -> None:
        """Test list_warnings convenience method."""
        mock_client._request.return_value = []

        manager = CatalogRepositoryLogManager(mock_client)
        manager.list_warnings()

        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]


class TestCatalogRepositoryLog:
    """Tests for CatalogRepositoryLog resource object."""

    def test_properties(self, mock_client: MagicMock) -> None:
        """Test log properties."""
        manager = CatalogRepositoryLogManager(mock_client)
        log = CatalogRepositoryLog(
            {"$key": 1, "catalog_repository": 1, "level": "error"},
            manager,
        )

        assert log.repository_key == 1
        assert log.is_error is True
        assert log.is_warning is False

    def test_warning_detection(self, mock_client: MagicMock) -> None:
        """Test warning detection."""
        manager = CatalogRepositoryLogManager(mock_client)
        log = CatalogRepositoryLog({"level": "warning"}, manager)

        assert log.is_warning is True
        assert log.is_error is False


class TestCatalogLogManager:
    """Tests for CatalogLogManager."""

    def test_list(self, mock_client: MagicMock) -> None:
        """Test listing logs."""
        mock_client._request.return_value = [
            {"$key": 1, "level": "message", "text": "Test log"},
        ]

        manager = CatalogLogManager(mock_client)
        logs = manager.list()

        assert len(logs) == 1
        assert isinstance(logs[0], CatalogLog)

    def test_list_scoped(self, mock_client: MagicMock) -> None:
        """Test scoped manager includes filter."""
        catalog_key = "abc123def456789012345678901234567890"
        mock_client._request.return_value = []

        manager = CatalogLogManager(mock_client, catalog_key=catalog_key)
        manager.list()

        call_args = mock_client._request.call_args
        assert f"catalog eq '{catalog_key}'" in call_args[1]["params"]["filter"]


class TestCatalogLog:
    """Tests for CatalogLog resource object."""

    def test_properties(self, mock_client: MagicMock) -> None:
        """Test log properties."""
        catalog_key = "abc123def456789012345678901234567890"
        manager = CatalogLogManager(mock_client)
        log = CatalogLog(
            {"$key": 1, "catalog": catalog_key, "level": "critical"},
            manager,
        )

        assert log.catalog_key == catalog_key
        assert log.is_error is True


# =============================================================================
# Client Integration Tests
# =============================================================================


class TestClientCatalogProperties:
    """Tests for VergeClient catalog properties."""

    def test_catalog_repositories_property(self, mock_client: MagicMock) -> None:
        """Test catalog_repositories property creates manager."""
        # Use actual VergeClient with patched connection
        from pyvergeos.client import VergeClient

        client = VergeClient.__new__(VergeClient)
        client._catalog_repositories = None
        client._connection = MagicMock()
        client._connection.is_connected = True

        manager = client.catalog_repositories
        assert isinstance(manager, CatalogRepositoryManager)
        assert client._catalog_repositories is manager

    def test_catalogs_property(self, mock_client: MagicMock) -> None:
        """Test catalogs property creates manager."""
        from pyvergeos.client import VergeClient

        client = VergeClient.__new__(VergeClient)
        client._catalogs = None
        client._connection = MagicMock()
        client._connection.is_connected = True

        manager = client.catalogs
        assert isinstance(manager, CatalogManager)
        assert client._catalogs is manager

    def test_catalog_logs_property(self, mock_client: MagicMock) -> None:
        """Test catalog_logs property creates manager."""
        from pyvergeos.client import VergeClient

        client = VergeClient.__new__(VergeClient)
        client._catalog_logs = None
        client._connection = MagicMock()
        client._connection.is_connected = True

        manager = client.catalog_logs
        assert isinstance(manager, CatalogLogManager)

    def test_catalog_repository_logs_property(self, mock_client: MagicMock) -> None:
        """Test catalog_repository_logs property creates manager."""
        from pyvergeos.client import VergeClient

        client = VergeClient.__new__(VergeClient)
        client._catalog_repository_logs = None
        client._connection = MagicMock()
        client._connection.is_connected = True

        manager = client.catalog_repository_logs
        assert isinstance(manager, CatalogRepositoryLogManager)

    def test_catalog_repository_status_property(self, mock_client: MagicMock) -> None:
        """Test catalog_repository_status property creates manager."""
        from pyvergeos.client import VergeClient

        client = VergeClient.__new__(VergeClient)
        client._catalog_repository_status = None
        client._connection = MagicMock()
        client._connection.is_connected = True

        manager = client.catalog_repository_status
        assert isinstance(manager, CatalogRepositoryStatusManager)
