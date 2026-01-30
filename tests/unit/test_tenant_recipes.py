"""Unit tests for tenant recipe management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_recipes import (
    TenantRecipe,
    TenantRecipeInstance,
    TenantRecipeInstanceManager,
    TenantRecipeLog,
    TenantRecipeLogManager,
    TenantRecipeManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def tenant_recipe_manager(mock_client):
    """Create a TenantRecipeManager with mock client."""
    return TenantRecipeManager(mock_client)


@pytest.fixture
def tenant_recipe_instance_manager(mock_client):
    """Create a TenantRecipeInstanceManager with mock client."""
    return TenantRecipeInstanceManager(mock_client)


@pytest.fixture
def scoped_instance_manager(mock_client):
    """Create a scoped TenantRecipeInstanceManager with mock client."""
    return TenantRecipeInstanceManager(
        mock_client, recipe_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def tenant_recipe_log_manager(mock_client):
    """Create a TenantRecipeLogManager with mock client."""
    return TenantRecipeLogManager(mock_client)


@pytest.fixture
def scoped_log_manager(mock_client):
    """Create a scoped TenantRecipeLogManager with mock client."""
    return TenantRecipeLogManager(
        mock_client, recipe_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def sample_tenant_recipe():
    """Sample tenant recipe data from API."""
    return {
        "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "id": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "name": "Standard Tenant",
        "description": "Standard tenant template",
        "icon": "building",
        "version": "1.0.0",
        "build": 3,
        "catalog": "abc123def456...",
        "catalog_display": "Local Catalog",
        "status": "online",
        "rstatus": "online",
        "downloaded": True,
        "update_available": False,
        "needs_republish": False,
        "preserve_certs": True,
        "tenant": 5,
        "tenant_display": "tenant-template",
        "tenant_snapshot": 1,
        "snapshot_display": "initial",
        "instances": 2,
        "creator": "admin",
    }


@pytest.fixture
def sample_tenant_recipe_not_downloaded():
    """Sample tenant recipe that is not downloaded."""
    return {
        "$key": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "id": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "name": "Enterprise Tenant",
        "description": "Enterprise tenant template",
        "version": "2.0.0",
        "downloaded": False,
        "update_available": True,
    }


@pytest.fixture
def sample_tenant_recipe_instance():
    """Sample tenant recipe instance data from API."""
    return {
        "$key": 1,
        "recipe": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "recipe_display": "Standard Tenant",
        "recipe_name": "Standard Tenant",
        "tenant": 10,
        "tenant_display": "my-tenant",
        "tenant_name": "my-tenant",
        "name": "my-tenant",
        "version": "1.0.0",
        "build": 3,
        "created": 1700000000,
        "modified": 1700001000,
    }


@pytest.fixture
def sample_tenant_recipe_log():
    """Sample tenant recipe log data from API."""
    return {
        "$key": 1,
        "tenant_recipe": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "tenant_recipe_display": "Standard Tenant",
        "level": "message",
        "text": "Recipe deployed successfully",
        "timestamp": 1700000000,
        "user": "admin",
    }


class TestTenantRecipe:
    """Tests for TenantRecipe model."""

    def test_key_is_string(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test that recipe key is a string (40-char hex)."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert isinstance(recipe.key, str)
        assert len(recipe.key) == 40

    def test_key_missing(self, tenant_recipe_manager):
        """Test key property raises ValueError when missing."""
        recipe = TenantRecipe({}, tenant_recipe_manager)
        with pytest.raises(ValueError, match="has no \\$key"):
            _ = recipe.key

    def test_is_downloaded_true(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test is_downloaded returns True when downloaded."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.is_downloaded is True

    def test_is_downloaded_false(self, tenant_recipe_manager, sample_tenant_recipe_not_downloaded):
        """Test is_downloaded returns False when not downloaded."""
        recipe = TenantRecipe(sample_tenant_recipe_not_downloaded, tenant_recipe_manager)
        assert recipe.is_downloaded is False

    def test_has_update_true(self, tenant_recipe_manager, sample_tenant_recipe_not_downloaded):
        """Test has_update returns True when update available."""
        recipe = TenantRecipe(sample_tenant_recipe_not_downloaded, tenant_recipe_manager)
        assert recipe.has_update is True

    def test_has_update_false(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test has_update returns False when no update available."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.has_update is False

    def test_status_info(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test status_info property."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.status_info == "online"

    def test_catalog_key(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test catalog_key property."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.catalog_key == "abc123def456..."

    def test_tenant_key(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test tenant_key property."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.tenant_key == 5

    def test_tenant_key_none(self, tenant_recipe_manager, sample_tenant_recipe_not_downloaded):
        """Test tenant_key returns None when not set."""
        recipe = TenantRecipe(sample_tenant_recipe_not_downloaded, tenant_recipe_manager)
        assert recipe.tenant_key is None

    def test_instance_count(self, tenant_recipe_manager, sample_tenant_recipe):
        """Test instance_count property."""
        recipe = TenantRecipe(sample_tenant_recipe, tenant_recipe_manager)
        assert recipe.instance_count == 2


class TestTenantRecipeManagerList:
    """Tests for TenantRecipeManager.list()."""

    def test_list_all(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test listing all recipes."""
        mock_client._request.return_value = [sample_tenant_recipe]

        result = tenant_recipe_manager.list()

        assert len(result) == 1
        assert result[0].name == "Standard Tenant"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "tenant_recipes"

    def test_list_empty(self, tenant_recipe_manager, mock_client):
        """Test listing when no recipes exist."""
        mock_client._request.return_value = None

        result = tenant_recipe_manager.list()

        assert result == []

    def test_list_with_filter(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_tenant_recipe]

        result = tenant_recipe_manager.list(filter="name eq 'Standard Tenant'")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "name eq 'Standard Tenant'"

    def test_list_with_downloaded_filter(
        self, tenant_recipe_manager, mock_client, sample_tenant_recipe
    ):
        """Test listing with downloaded filter."""
        mock_client._request.return_value = [sample_tenant_recipe]

        result = tenant_recipe_manager.list(downloaded=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "downloaded eq 1" in args[1]["params"]["filter"]


class TestTenantRecipeManagerGet:
    """Tests for TenantRecipeManager.get()."""

    def test_get_by_key(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test getting recipe by key."""
        mock_client._request.return_value = [sample_tenant_recipe]

        result = tenant_recipe_manager.get(key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result.name == "Standard Tenant"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert "id eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_get_by_name(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test getting recipe by name."""
        mock_client._request.return_value = [sample_tenant_recipe]

        result = tenant_recipe_manager.get(name="Standard Tenant")

        assert result.name == "Standard Tenant"
        args = mock_client._request.call_args
        assert "name eq 'Standard Tenant'" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, tenant_recipe_manager, mock_client):
        """Test getting non-existent recipe by key."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            tenant_recipe_manager.get(key="nonexistent")

    def test_get_no_key_or_name(self, tenant_recipe_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            tenant_recipe_manager.get()


class TestTenantRecipeManagerUpdate:
    """Tests for TenantRecipeManager.update()."""

    def test_update_description(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test updating recipe description."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_tenant_recipe],  # Get updated recipe
        ]

        result = tenant_recipe_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            description="New description",
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in update_call[0][1]
        assert update_call[1]["json_data"]["description"] == "New description"

    def test_update_preserve_certs(self, tenant_recipe_manager, mock_client, sample_tenant_recipe):
        """Test updating preserve_certs setting."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_tenant_recipe],  # Get updated recipe
        ]

        tenant_recipe_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            preserve_certs=False,
        )

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["preserve_certs"] is False


class TestTenantRecipeManagerDelete:
    """Tests for TenantRecipeManager.delete()."""

    def test_delete(self, tenant_recipe_manager, mock_client):
        """Test deleting a recipe."""
        mock_client._request.return_value = None

        tenant_recipe_manager.delete("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in delete_call[0][1]


class TestTenantRecipeManagerActions:
    """Tests for tenant recipe actions."""

    def test_download(self, tenant_recipe_manager, mock_client):
        """Test downloading a recipe."""
        mock_client._request.return_value = {"task": 123}

        result = tenant_recipe_manager.download("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[0][0] == "PUT"
        assert "action=download" in action_call[0][1]

    def test_get_instances_manager(self, tenant_recipe_manager, mock_client):
        """Test getting a scoped instances manager."""
        inst_mgr = tenant_recipe_manager.instances("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(inst_mgr, TenantRecipeInstanceManager)
        assert inst_mgr._recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_get_logs_manager(self, tenant_recipe_manager, mock_client):
        """Test getting a scoped logs manager."""
        log_mgr = tenant_recipe_manager.logs("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(log_mgr, TenantRecipeLogManager)
        assert log_mgr._recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"


# =============================================================================
# Tenant Recipe Instance Tests
# =============================================================================


class TestTenantRecipeInstance:
    """Tests for TenantRecipeInstance model."""

    def test_recipe_key(self, tenant_recipe_instance_manager, sample_tenant_recipe_instance):
        """Test recipe_key property."""
        inst = TenantRecipeInstance(sample_tenant_recipe_instance, tenant_recipe_instance_manager)
        assert inst.recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_tenant_key(self, tenant_recipe_instance_manager, sample_tenant_recipe_instance):
        """Test tenant_key property."""
        inst = TenantRecipeInstance(sample_tenant_recipe_instance, tenant_recipe_instance_manager)
        assert inst.tenant_key == 10


class TestTenantRecipeInstanceManagerList:
    """Tests for TenantRecipeInstanceManager.list()."""

    def test_list_all(
        self, tenant_recipe_instance_manager, mock_client, sample_tenant_recipe_instance
    ):
        """Test listing all instances."""
        mock_client._request.return_value = [sample_tenant_recipe_instance]

        result = tenant_recipe_instance_manager.list()

        assert len(result) == 1
        assert result[0].name == "my-tenant"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "tenant_recipe_instances"

    def test_list_scoped_to_recipe(
        self, scoped_instance_manager, mock_client, sample_tenant_recipe_instance
    ):
        """Test listing instances scoped to a recipe."""
        mock_client._request.return_value = [sample_tenant_recipe_instance]

        result = scoped_instance_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "recipe eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]


class TestTenantRecipeInstanceManagerCreate:
    """Tests for TenantRecipeInstanceManager.create()."""

    def test_create(
        self, tenant_recipe_instance_manager, mock_client, sample_tenant_recipe_instance
    ):
        """Test creating a recipe instance."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create
            sample_tenant_recipe_instance,  # Get created
        ]

        result = tenant_recipe_instance_manager.create(
            recipe="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            name="my-tenant",
            answers={"storage_gb": 500},
        )

        assert result.name == "my-tenant"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "tenant_recipe_instances"
        body = create_call[1]["json_data"]
        assert body["recipe"] == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert body["name"] == "my-tenant"
        assert body["answers"] == {"storage_gb": 500}


# =============================================================================
# Tenant Recipe Log Tests
# =============================================================================


class TestTenantRecipeLog:
    """Tests for TenantRecipeLog model."""

    def test_recipe_key(self, tenant_recipe_log_manager, sample_tenant_recipe_log):
        """Test recipe_key property."""
        log = TenantRecipeLog(sample_tenant_recipe_log, tenant_recipe_log_manager)
        assert log.recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_is_error_true(self, tenant_recipe_log_manager, sample_tenant_recipe_log):
        """Test is_error returns True for error level."""
        sample_tenant_recipe_log["level"] = "error"
        log = TenantRecipeLog(sample_tenant_recipe_log, tenant_recipe_log_manager)
        assert log.is_error is True

    def test_is_error_false(self, tenant_recipe_log_manager, sample_tenant_recipe_log):
        """Test is_error returns False for message level."""
        log = TenantRecipeLog(sample_tenant_recipe_log, tenant_recipe_log_manager)
        assert log.is_error is False

    def test_is_warning_true(self, tenant_recipe_log_manager, sample_tenant_recipe_log):
        """Test is_warning returns True for warning level."""
        sample_tenant_recipe_log["level"] = "warning"
        log = TenantRecipeLog(sample_tenant_recipe_log, tenant_recipe_log_manager)
        assert log.is_warning is True


class TestTenantRecipeLogManagerList:
    """Tests for TenantRecipeLogManager.list()."""

    def test_list_all(self, tenant_recipe_log_manager, mock_client, sample_tenant_recipe_log):
        """Test listing all logs."""
        mock_client._request.return_value = [sample_tenant_recipe_log]

        result = tenant_recipe_log_manager.list()

        assert len(result) == 1
        assert result[0].text == "Recipe deployed successfully"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "tenant_recipe_logs"

    def test_list_scoped_to_recipe(self, scoped_log_manager, mock_client, sample_tenant_recipe_log):
        """Test listing logs scoped to a recipe."""
        mock_client._request.return_value = [sample_tenant_recipe_log]

        result = scoped_log_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert (
            "tenant_recipe eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'"
            in args[1]["params"]["filter"]
        )


class TestTenantRecipeLogManagerHelpers:
    """Tests for TenantRecipeLogManager helper methods."""

    def test_list_errors(self, scoped_log_manager, mock_client, sample_tenant_recipe_log):
        """Test list_errors helper."""
        sample_tenant_recipe_log["level"] = "error"
        mock_client._request.return_value = [sample_tenant_recipe_log]

        result = scoped_log_manager.list_errors()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "(level eq 'error') or (level eq 'critical')" in args[1]["params"]["filter"]

    def test_list_warnings(self, scoped_log_manager, mock_client, sample_tenant_recipe_log):
        """Test list_warnings helper."""
        sample_tenant_recipe_log["level"] = "warning"
        mock_client._request.return_value = [sample_tenant_recipe_log]

        result = scoped_log_manager.list_warnings()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "level eq 'warning'" in args[1]["params"]["filter"]
