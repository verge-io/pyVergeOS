"""Unit tests for VM recipe management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.vm_recipes import (
    VmRecipe,
    VmRecipeInstance,
    VmRecipeInstanceManager,
    VmRecipeLog,
    VmRecipeLogManager,
    VmRecipeManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def vm_recipe_manager(mock_client):
    """Create a VmRecipeManager with mock client."""
    return VmRecipeManager(mock_client)


@pytest.fixture
def vm_recipe_instance_manager(mock_client):
    """Create a VmRecipeInstanceManager with mock client."""
    return VmRecipeInstanceManager(mock_client)


@pytest.fixture
def scoped_instance_manager(mock_client):
    """Create a scoped VmRecipeInstanceManager with mock client."""
    return VmRecipeInstanceManager(
        mock_client, recipe_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def vm_recipe_log_manager(mock_client):
    """Create a VmRecipeLogManager with mock client."""
    return VmRecipeLogManager(mock_client)


@pytest.fixture
def scoped_log_manager(mock_client):
    """Create a scoped VmRecipeLogManager with mock client."""
    return VmRecipeLogManager(mock_client, recipe_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")


@pytest.fixture
def sample_vm_recipe():
    """Sample VM recipe data from API."""
    return {
        "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "id": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "name": "Ubuntu Server",
        "description": "Ubuntu Server LTS",
        "icon": "server",
        "version": "1.0.0",
        "build": 5,
        "catalog": "abc123def456...",
        "catalog_display": "Local Catalog",
        "status": "online",
        "rstatus": "online",
        "downloaded": True,
        "update_available": False,
        "needs_republish": False,
        "vm": 10,
        "vm_display": "ubuntu-template",
        "vm_snapshot": 1,
        "snapshot_display": "initial",
        "instances": 3,
        "creator": "admin",
    }


@pytest.fixture
def sample_vm_recipe_not_downloaded():
    """Sample VM recipe that is not downloaded."""
    return {
        "$key": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "id": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "name": "CentOS 7",
        "description": "CentOS 7 Latest",
        "version": "1.0.0",
        "downloaded": False,
        "update_available": True,
    }


@pytest.fixture
def sample_vm_recipe_instance():
    """Sample VM recipe instance data from API."""
    return {
        "$key": 1,
        "recipe": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "recipe_display": "Ubuntu Server",
        "recipe_name": "Ubuntu Server",
        "vm": 10,
        "vm_display": "my-ubuntu",
        "vm_name": "my-ubuntu",
        "name": "my-ubuntu",
        "version": "1.0.0",
        "build": 5,
        "auto_update": True,
        "created": 1700000000,
        "modified": 1700001000,
    }


@pytest.fixture
def sample_vm_recipe_log():
    """Sample VM recipe log data from API."""
    return {
        "$key": 1,
        "vm_recipe": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "vm_recipe_display": "Ubuntu Server",
        "level": "message",
        "text": "Recipe deployed successfully",
        "timestamp": 1700000000,
        "user": "admin",
    }


class TestVmRecipe:
    """Tests for VmRecipe model."""

    def test_key_is_string(self, vm_recipe_manager, sample_vm_recipe):
        """Test that recipe key is a string (40-char hex)."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert isinstance(recipe.key, str)
        assert len(recipe.key) == 40

    def test_key_missing(self, vm_recipe_manager):
        """Test key property raises ValueError when missing."""
        recipe = VmRecipe({}, vm_recipe_manager)
        with pytest.raises(ValueError, match="has no \\$key"):
            _ = recipe.key

    def test_is_downloaded_true(self, vm_recipe_manager, sample_vm_recipe):
        """Test is_downloaded returns True when downloaded."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.is_downloaded is True

    def test_is_downloaded_false(self, vm_recipe_manager, sample_vm_recipe_not_downloaded):
        """Test is_downloaded returns False when not downloaded."""
        recipe = VmRecipe(sample_vm_recipe_not_downloaded, vm_recipe_manager)
        assert recipe.is_downloaded is False

    def test_has_update_true(self, vm_recipe_manager, sample_vm_recipe_not_downloaded):
        """Test has_update returns True when update available."""
        recipe = VmRecipe(sample_vm_recipe_not_downloaded, vm_recipe_manager)
        assert recipe.has_update is True

    def test_has_update_false(self, vm_recipe_manager, sample_vm_recipe):
        """Test has_update returns False when no update available."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.has_update is False

    def test_status_info(self, vm_recipe_manager, sample_vm_recipe):
        """Test status_info property."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.status_info == "online"

    def test_catalog_key(self, vm_recipe_manager, sample_vm_recipe):
        """Test catalog_key property."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.catalog_key == "abc123def456..."

    def test_vm_key(self, vm_recipe_manager, sample_vm_recipe):
        """Test vm_key property."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.vm_key == 10

    def test_vm_key_none(self, vm_recipe_manager, sample_vm_recipe_not_downloaded):
        """Test vm_key returns None when not set."""
        recipe = VmRecipe(sample_vm_recipe_not_downloaded, vm_recipe_manager)
        assert recipe.vm_key is None

    def test_instance_count(self, vm_recipe_manager, sample_vm_recipe):
        """Test instance_count property."""
        recipe = VmRecipe(sample_vm_recipe, vm_recipe_manager)
        assert recipe.instance_count == 3


class TestVmRecipeManagerList:
    """Tests for VmRecipeManager.list()."""

    def test_list_all(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test listing all recipes."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.list()

        assert len(result) == 1
        assert result[0].name == "Ubuntu Server"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_recipes"

    def test_list_empty(self, vm_recipe_manager, mock_client):
        """Test listing when no recipes exist."""
        mock_client._request.return_value = None

        result = vm_recipe_manager.list()

        assert result == []

    def test_list_with_filter(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.list(filter="name eq 'Ubuntu Server'")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "name eq 'Ubuntu Server'"

    def test_list_with_downloaded_filter(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test listing with downloaded filter."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.list(downloaded=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "downloaded eq 1" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVmRecipeManagerGet:
    """Tests for VmRecipeManager.get()."""

    def test_get_by_key(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test getting recipe by key."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.get(key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result.name == "Ubuntu Server"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert "id eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_get_by_name(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test getting recipe by name."""
        mock_client._request.return_value = [sample_vm_recipe]

        result = vm_recipe_manager.get(name="Ubuntu Server")

        assert result.name == "Ubuntu Server"
        args = mock_client._request.call_args
        assert "name eq 'Ubuntu Server'" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, vm_recipe_manager, mock_client):
        """Test getting non-existent recipe by key."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            vm_recipe_manager.get(key="nonexistent")

    def test_get_not_found_by_name(self, vm_recipe_manager, mock_client):
        """Test getting non-existent recipe by name."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            vm_recipe_manager.get(name="nonexistent")

    def test_get_no_key_or_name(self, vm_recipe_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            vm_recipe_manager.get()


class TestVmRecipeManagerUpdate:
    """Tests for VmRecipeManager.update()."""

    def test_update_description(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test updating recipe description."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_vm_recipe],  # Get updated recipe
        ]

        result = vm_recipe_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            description="New description",
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in update_call[0][1]
        assert update_call[1]["json_data"]["description"] == "New description"

    def test_update_no_changes(self, vm_recipe_manager, mock_client, sample_vm_recipe):
        """Test update with no changes."""
        mock_client._request.return_value = [sample_vm_recipe]

        vm_recipe_manager.update("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        # Should only call get, not update
        assert mock_client._request.call_count == 1


class TestVmRecipeManagerDelete:
    """Tests for VmRecipeManager.delete()."""

    def test_delete(self, vm_recipe_manager, mock_client):
        """Test deleting a recipe."""
        mock_client._request.return_value = None

        vm_recipe_manager.delete("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in delete_call[0][1]


class TestVmRecipeManagerActions:
    """Tests for VM recipe actions."""

    def test_download(self, vm_recipe_manager, mock_client):
        """Test downloading a recipe."""
        mock_client._request.return_value = {"task": 123}

        result = vm_recipe_manager.download("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[0][0] == "PUT"
        assert "action=download" in action_call[0][1]

    def test_get_instances_manager(self, vm_recipe_manager, mock_client):
        """Test getting a scoped instances manager."""
        inst_mgr = vm_recipe_manager.instances("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(inst_mgr, VmRecipeInstanceManager)
        assert inst_mgr._recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_get_logs_manager(self, vm_recipe_manager, mock_client):
        """Test getting a scoped logs manager."""
        log_mgr = vm_recipe_manager.logs("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(log_mgr, VmRecipeLogManager)
        assert log_mgr._recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"


# =============================================================================
# VM Recipe Instance Tests
# =============================================================================


class TestVmRecipeInstance:
    """Tests for VmRecipeInstance model."""

    def test_recipe_key(self, vm_recipe_instance_manager, sample_vm_recipe_instance):
        """Test recipe_key property."""
        inst = VmRecipeInstance(sample_vm_recipe_instance, vm_recipe_instance_manager)
        assert inst.recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_vm_key(self, vm_recipe_instance_manager, sample_vm_recipe_instance):
        """Test vm_key property."""
        inst = VmRecipeInstance(sample_vm_recipe_instance, vm_recipe_instance_manager)
        assert inst.vm_key == 10

    def test_is_auto_update_true(self, vm_recipe_instance_manager, sample_vm_recipe_instance):
        """Test is_auto_update returns True when enabled."""
        inst = VmRecipeInstance(sample_vm_recipe_instance, vm_recipe_instance_manager)
        assert inst.is_auto_update is True

    def test_is_auto_update_false(self, vm_recipe_instance_manager, sample_vm_recipe_instance):
        """Test is_auto_update returns False when disabled."""
        sample_vm_recipe_instance["auto_update"] = False
        inst = VmRecipeInstance(sample_vm_recipe_instance, vm_recipe_instance_manager)
        assert inst.is_auto_update is False


class TestVmRecipeInstanceManagerList:
    """Tests for VmRecipeInstanceManager.list()."""

    def test_list_all(self, vm_recipe_instance_manager, mock_client, sample_vm_recipe_instance):
        """Test listing all instances."""
        mock_client._request.return_value = [sample_vm_recipe_instance]

        result = vm_recipe_instance_manager.list()

        assert len(result) == 1
        assert result[0].name == "my-ubuntu"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_recipe_instances"

    def test_list_empty(self, vm_recipe_instance_manager, mock_client):
        """Test listing when no instances exist."""
        mock_client._request.return_value = None

        result = vm_recipe_instance_manager.list()

        assert result == []

    def test_list_scoped_to_recipe(
        self, scoped_instance_manager, mock_client, sample_vm_recipe_instance
    ):
        """Test listing instances scoped to a recipe."""
        mock_client._request.return_value = [sample_vm_recipe_instance]

        result = scoped_instance_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "recipe eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]


class TestVmRecipeInstanceManagerGet:
    """Tests for VmRecipeInstanceManager.get()."""

    def test_get_by_key(self, vm_recipe_instance_manager, mock_client, sample_vm_recipe_instance):
        """Test getting instance by key."""
        mock_client._request.return_value = sample_vm_recipe_instance

        result = vm_recipe_instance_manager.get(key=1)

        assert result.name == "my-ubuntu"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_recipe_instances/1"

    def test_get_by_name(self, vm_recipe_instance_manager, mock_client, sample_vm_recipe_instance):
        """Test getting instance by name."""
        mock_client._request.return_value = [sample_vm_recipe_instance]

        result = vm_recipe_instance_manager.get(name="my-ubuntu")

        assert result.name == "my-ubuntu"
        args = mock_client._request.call_args
        assert "name eq 'my-ubuntu'" in args[1]["params"]["filter"]

    def test_get_not_found(self, vm_recipe_instance_manager, mock_client):
        """Test getting non-existent instance."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            vm_recipe_instance_manager.get(key=999)

    def test_get_no_key_or_name(self, vm_recipe_instance_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            vm_recipe_instance_manager.get()


class TestVmRecipeInstanceManagerCreate:
    """Tests for VmRecipeInstanceManager.create()."""

    def test_create(self, vm_recipe_instance_manager, mock_client, sample_vm_recipe_instance):
        """Test creating a recipe instance."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create
            sample_vm_recipe_instance,  # Get created
        ]

        result = vm_recipe_instance_manager.create(
            recipe="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            name="my-ubuntu",
            answers={"ram": 4096},
            auto_update=True,
        )

        assert result.name == "my-ubuntu"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "vm_recipe_instances"
        body = create_call[1]["json_data"]
        assert body["recipe"] == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert body["name"] == "my-ubuntu"
        assert body["answers"] == {"ram": 4096}
        assert body["auto_update"] is True


class TestVmRecipeInstanceManagerDelete:
    """Tests for VmRecipeInstanceManager.delete()."""

    def test_delete(self, vm_recipe_instance_manager, mock_client):
        """Test deleting an instance."""
        mock_client._request.return_value = None

        vm_recipe_instance_manager.delete(1)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vm_recipe_instances/1"


# =============================================================================
# VM Recipe Log Tests
# =============================================================================


class TestVmRecipeLog:
    """Tests for VmRecipeLog model."""

    def test_recipe_key(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test recipe_key property."""
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.recipe_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_is_error_true(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test is_error returns True for error level."""
        sample_vm_recipe_log["level"] = "error"
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.is_error is True

    def test_is_error_critical(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test is_error returns True for critical level."""
        sample_vm_recipe_log["level"] = "critical"
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.is_error is True

    def test_is_error_false(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test is_error returns False for message level."""
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.is_error is False

    def test_is_warning_true(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test is_warning returns True for warning level."""
        sample_vm_recipe_log["level"] = "warning"
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.is_warning is True

    def test_is_warning_false(self, vm_recipe_log_manager, sample_vm_recipe_log):
        """Test is_warning returns False for message level."""
        log = VmRecipeLog(sample_vm_recipe_log, vm_recipe_log_manager)
        assert log.is_warning is False


class TestVmRecipeLogManagerList:
    """Tests for VmRecipeLogManager.list()."""

    def test_list_all(self, vm_recipe_log_manager, mock_client, sample_vm_recipe_log):
        """Test listing all logs."""
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = vm_recipe_log_manager.list()

        assert len(result) == 1
        assert result[0].text == "Recipe deployed successfully"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_recipe_logs"

    def test_list_empty(self, vm_recipe_log_manager, mock_client):
        """Test listing when no logs exist."""
        mock_client._request.return_value = None

        result = vm_recipe_log_manager.list()

        assert result == []

    def test_list_scoped_to_recipe(self, scoped_log_manager, mock_client, sample_vm_recipe_log):
        """Test listing logs scoped to a recipe."""
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = scoped_log_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert (
            "vm_recipe eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]
        )

    def test_list_with_level_filter(self, vm_recipe_log_manager, mock_client, sample_vm_recipe_log):
        """Test listing with level filter."""
        sample_vm_recipe_log["level"] = "error"
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = vm_recipe_log_manager.list(level="error")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "level eq 'error'" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, vm_recipe_log_manager, mock_client, sample_vm_recipe_log):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = vm_recipe_log_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVmRecipeLogManagerGet:
    """Tests for VmRecipeLogManager.get()."""

    def test_get_by_key(self, vm_recipe_log_manager, mock_client, sample_vm_recipe_log):
        """Test getting log by key."""
        mock_client._request.return_value = sample_vm_recipe_log

        result = vm_recipe_log_manager.get(key=1)

        assert result.text == "Recipe deployed successfully"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_recipe_logs/1"

    def test_get_not_found(self, vm_recipe_log_manager, mock_client):
        """Test getting non-existent log."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            vm_recipe_log_manager.get(key=999)

    def test_get_no_key(self, vm_recipe_log_manager):
        """Test get without key raises ValueError."""
        with pytest.raises(ValueError, match="Key must be provided"):
            vm_recipe_log_manager.get()


class TestVmRecipeLogManagerHelpers:
    """Tests for VmRecipeLogManager helper methods."""

    def test_list_errors(self, scoped_log_manager, mock_client, sample_vm_recipe_log):
        """Test list_errors helper."""
        sample_vm_recipe_log["level"] = "error"
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = scoped_log_manager.list_errors()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "(level eq 'error') or (level eq 'critical')" in args[1]["params"]["filter"]

    def test_list_warnings(self, scoped_log_manager, mock_client, sample_vm_recipe_log):
        """Test list_warnings helper."""
        sample_vm_recipe_log["level"] = "warning"
        mock_client._request.return_value = [sample_vm_recipe_log]

        result = scoped_log_manager.list_warnings()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "level eq 'warning'" in args[1]["params"]["filter"]
