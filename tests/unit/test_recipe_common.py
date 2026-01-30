"""Unit tests for recipe questions and sections."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.recipe_common import (
    RecipeQuestion,
    RecipeQuestionManager,
    RecipeSection,
    RecipeSectionManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def recipe_question_manager(mock_client):
    """Create a RecipeQuestionManager with mock client."""
    return RecipeQuestionManager(mock_client)


@pytest.fixture
def scoped_question_manager(mock_client):
    """Create a RecipeQuestionManager scoped to a recipe."""
    return RecipeQuestionManager(
        mock_client, recipe_ref="vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def section_scoped_question_manager(mock_client):
    """Create a RecipeQuestionManager scoped to a section."""
    return RecipeQuestionManager(mock_client, section_key=123)


@pytest.fixture
def recipe_section_manager(mock_client):
    """Create a RecipeSectionManager with mock client."""
    return RecipeSectionManager(mock_client)


@pytest.fixture
def scoped_section_manager(mock_client):
    """Create a RecipeSectionManager scoped to a recipe."""
    return RecipeSectionManager(
        mock_client, recipe_ref="vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def sample_recipe_question():
    """Sample recipe question data from API."""
    return {
        "$key": 1,
        "recipe": "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "section": 10,
        "section_name": "Virtual Machine",
        "name": "YB_CPU_CORES",
        "display": "CPU Cores",
        "hint": "Number of CPU cores",
        "help": "Select the number of CPU cores for this VM",
        "note": "More cores = better performance",
        "type": "num",
        "default": "2",
        "required": True,
        "enabled": True,
        "readonly": False,
        "orderid": 1,
        "min": 1,
        "max": 64,
    }


@pytest.fixture
def sample_password_question():
    """Sample password question data from API."""
    return {
        "$key": 2,
        "recipe": "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "section": 10,
        "name": "PASSWORD",
        "display": "Password",
        "type": "password",
        "required": True,
        "enabled": True,
        "readonly": True,
    }


@pytest.fixture
def sample_list_question():
    """Sample list question data from API."""
    return {
        "$key": 3,
        "recipe": "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "section": 10,
        "name": "DISK_TYPE",
        "display": "Disk Type",
        "type": "list",
        "required": False,
        "enabled": True,
        "list": {"ssd": "SSD", "hdd": "HDD", "nvme": "NVMe"},
    }


@pytest.fixture
def sample_hidden_question():
    """Sample hidden question data from API."""
    return {
        "$key": 4,
        "recipe": "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "section": 10,
        "name": "YB_INTERNAL",
        "display": "Internal",
        "type": "hidden",
        "default": "true",
        "enabled": True,
    }


@pytest.fixture
def sample_recipe_section():
    """Sample recipe section data from API."""
    return {
        "$key": 10,
        "recipe": "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "name": "Virtual Machine",
        "description": "Basic VM configuration settings",
        "orderid": 1,
    }


class TestRecipeQuestion:
    """Tests for RecipeQuestion model."""

    def test_recipe_ref(self, recipe_question_manager, sample_recipe_question):
        """Test recipe_ref property."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.recipe_ref == "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_section_key(self, recipe_question_manager, sample_recipe_question):
        """Test section_key property."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.section_key == 10

    def test_question_type(self, recipe_question_manager, sample_recipe_question):
        """Test question_type property."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.question_type == "num"

    def test_is_required_true(self, recipe_question_manager, sample_recipe_question):
        """Test is_required returns True when required."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_required is True

    def test_is_required_false(self, recipe_question_manager, sample_list_question):
        """Test is_required returns False when not required."""
        question = RecipeQuestion(sample_list_question, recipe_question_manager)
        assert question.is_required is False

    def test_is_enabled_true(self, recipe_question_manager, sample_recipe_question):
        """Test is_enabled returns True when enabled."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_enabled is True

    def test_is_enabled_false(self, recipe_question_manager, sample_recipe_question):
        """Test is_enabled returns False when disabled."""
        sample_recipe_question["enabled"] = False
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_enabled is False

    def test_is_readonly_true(self, recipe_question_manager, sample_password_question):
        """Test is_readonly returns True when readonly."""
        question = RecipeQuestion(sample_password_question, recipe_question_manager)
        assert question.is_readonly is True

    def test_is_readonly_false(self, recipe_question_manager, sample_recipe_question):
        """Test is_readonly returns False when not readonly."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_readonly is False

    def test_is_password_true(self, recipe_question_manager, sample_password_question):
        """Test is_password returns True for password type."""
        question = RecipeQuestion(sample_password_question, recipe_question_manager)
        assert question.is_password is True

    def test_is_password_false(self, recipe_question_manager, sample_recipe_question):
        """Test is_password returns False for non-password type."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_password is False

    def test_is_hidden_true(self, recipe_question_manager, sample_hidden_question):
        """Test is_hidden returns True for hidden type."""
        question = RecipeQuestion(sample_hidden_question, recipe_question_manager)
        assert question.is_hidden is True

    def test_is_hidden_false(self, recipe_question_manager, sample_recipe_question):
        """Test is_hidden returns False for non-hidden type."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.is_hidden is False

    def test_list_options(self, recipe_question_manager, sample_list_question):
        """Test list_options returns options for list type."""
        question = RecipeQuestion(sample_list_question, recipe_question_manager)
        assert question.list_options == {"ssd": "SSD", "hdd": "HDD", "nvme": "NVMe"}

    def test_list_options_none_for_non_list(
        self, recipe_question_manager, sample_recipe_question
    ):
        """Test list_options returns None for non-list type."""
        question = RecipeQuestion(sample_recipe_question, recipe_question_manager)
        assert question.list_options is None


class TestRecipeQuestionManagerList:
    """Tests for RecipeQuestionManager.list()."""

    def test_list_all(self, recipe_question_manager, mock_client, sample_recipe_question):
        """Test listing all questions."""
        mock_client._request.return_value = [sample_recipe_question]

        result = recipe_question_manager.list()

        assert len(result) == 1
        assert result[0].name == "YB_CPU_CORES"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "recipe_questions"
        # Should sort by orderid
        assert args[1]["params"]["sort"] == "+orderid"

    def test_list_empty(self, recipe_question_manager, mock_client):
        """Test listing when no questions exist."""
        mock_client._request.return_value = None

        result = recipe_question_manager.list()

        assert result == []

    def test_list_scoped_to_recipe(
        self, scoped_question_manager, mock_client, sample_recipe_question
    ):
        """Test listing questions scoped to a recipe."""
        mock_client._request.return_value = [sample_recipe_question]

        result = scoped_question_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert (
            "recipe eq 'vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554'"
            in args[1]["params"]["filter"]
        )

    def test_list_scoped_to_section(
        self, section_scoped_question_manager, mock_client, sample_recipe_question
    ):
        """Test listing questions scoped to a section."""
        mock_client._request.return_value = [sample_recipe_question]

        result = section_scoped_question_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "section eq 123" in args[1]["params"]["filter"]

    def test_list_with_enabled_filter(
        self, recipe_question_manager, mock_client, sample_recipe_question
    ):
        """Test listing with enabled filter."""
        mock_client._request.return_value = [sample_recipe_question]

        result = recipe_question_manager.list(enabled=True)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "enabled eq 1" in args[1]["params"]["filter"]


class TestRecipeQuestionManagerGet:
    """Tests for RecipeQuestionManager.get()."""

    def test_get_by_key(
        self, recipe_question_manager, mock_client, sample_recipe_question
    ):
        """Test getting question by key."""
        mock_client._request.return_value = sample_recipe_question

        result = recipe_question_manager.get(key=1)

        assert result.name == "YB_CPU_CORES"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "recipe_questions/1"

    def test_get_by_name(
        self, recipe_question_manager, mock_client, sample_recipe_question
    ):
        """Test getting question by name."""
        mock_client._request.return_value = [sample_recipe_question]

        result = recipe_question_manager.get(name="YB_CPU_CORES")

        assert result.name == "YB_CPU_CORES"
        args = mock_client._request.call_args
        assert "name eq 'YB_CPU_CORES'" in args[1]["params"]["filter"]

    def test_get_not_found(self, recipe_question_manager, mock_client):
        """Test getting non-existent question."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            recipe_question_manager.get(key=999)

    def test_get_no_key_or_name(self, recipe_question_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            recipe_question_manager.get()


class TestRecipeQuestionManagerCreate:
    """Tests for RecipeQuestionManager.create()."""

    def test_create(self, recipe_question_manager, mock_client, sample_recipe_question):
        """Test creating a question."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create
            sample_recipe_question,  # Get created
        ]

        result = recipe_question_manager.create(
            name="YB_CPU_CORES",
            recipe_ref="vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            section=10,
            question_type="num",
            display="CPU Cores",
            default="2",
            required=True,
            min_value=1,
            max_value=64,
        )

        assert result.name == "YB_CPU_CORES"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "recipe_questions"
        body = create_call[1]["json_data"]
        assert body["name"] == "YB_CPU_CORES"
        assert body["recipe"] == "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert body["section"] == 10
        assert body["type"] == "num"
        assert body["display"] == "CPU Cores"
        assert body["default"] == "2"
        assert body["required"] is True
        assert body["min"] == 1
        assert body["max"] == 64


class TestRecipeQuestionManagerUpdate:
    """Tests for RecipeQuestionManager.update()."""

    def test_update(self, recipe_question_manager, mock_client, sample_recipe_question):
        """Test updating a question."""
        mock_client._request.side_effect = [
            None,  # Update
            sample_recipe_question,  # Get updated
        ]

        result = recipe_question_manager.update(
            key=1,
            display="Number of CPU Cores",
            default="4",
            required=False,
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "recipe_questions/1"
        body = update_call[1]["json_data"]
        assert body["display"] == "Number of CPU Cores"
        assert body["default"] == "4"
        assert body["required"] is False


class TestRecipeQuestionManagerDelete:
    """Tests for RecipeQuestionManager.delete()."""

    def test_delete(self, recipe_question_manager, mock_client):
        """Test deleting a question."""
        mock_client._request.return_value = None

        recipe_question_manager.delete(1)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "recipe_questions/1"


# =============================================================================
# Recipe Section Tests
# =============================================================================


class TestRecipeSection:
    """Tests for RecipeSection model."""

    def test_recipe_ref(self, recipe_section_manager, sample_recipe_section):
        """Test recipe_ref property."""
        section = RecipeSection(sample_recipe_section, recipe_section_manager)
        assert section.recipe_ref == "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"


class TestRecipeSectionManagerList:
    """Tests for RecipeSectionManager.list()."""

    def test_list_all(self, recipe_section_manager, mock_client, sample_recipe_section):
        """Test listing all sections."""
        mock_client._request.return_value = [sample_recipe_section]

        result = recipe_section_manager.list()

        assert len(result) == 1
        assert result[0].name == "Virtual Machine"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "recipe_sections"
        # Should sort by orderid
        assert args[1]["params"]["sort"] == "+orderid"

    def test_list_empty(self, recipe_section_manager, mock_client):
        """Test listing when no sections exist."""
        mock_client._request.return_value = None

        result = recipe_section_manager.list()

        assert result == []

    def test_list_scoped_to_recipe(
        self, scoped_section_manager, mock_client, sample_recipe_section
    ):
        """Test listing sections scoped to a recipe."""
        mock_client._request.return_value = [sample_recipe_section]

        result = scoped_section_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert (
            "recipe eq 'vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554'"
            in args[1]["params"]["filter"]
        )


class TestRecipeSectionManagerGet:
    """Tests for RecipeSectionManager.get()."""

    def test_get_by_key(self, recipe_section_manager, mock_client, sample_recipe_section):
        """Test getting section by key."""
        mock_client._request.return_value = sample_recipe_section

        result = recipe_section_manager.get(key=10)

        assert result.name == "Virtual Machine"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "recipe_sections/10"

    def test_get_by_name(
        self, recipe_section_manager, mock_client, sample_recipe_section
    ):
        """Test getting section by name."""
        mock_client._request.return_value = [sample_recipe_section]

        result = recipe_section_manager.get(name="Virtual Machine")

        assert result.name == "Virtual Machine"
        args = mock_client._request.call_args
        assert "name eq 'Virtual Machine'" in args[1]["params"]["filter"]

    def test_get_not_found(self, recipe_section_manager, mock_client):
        """Test getting non-existent section."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            recipe_section_manager.get(key=999)

    def test_get_no_key_or_name(self, recipe_section_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            recipe_section_manager.get()


class TestRecipeSectionManagerCreate:
    """Tests for RecipeSectionManager.create()."""

    def test_create(self, recipe_section_manager, mock_client, sample_recipe_section):
        """Test creating a section."""
        mock_client._request.side_effect = [
            {"$key": 10},  # Create
            sample_recipe_section,  # Get created
        ]

        result = recipe_section_manager.create(
            name="Virtual Machine",
            recipe_ref="vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            description="Basic VM configuration settings",
        )

        assert result.name == "Virtual Machine"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "recipe_sections"
        body = create_call[1]["json_data"]
        assert body["name"] == "Virtual Machine"
        assert body["recipe"] == "vm_recipes/8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        assert body["description"] == "Basic VM configuration settings"


class TestRecipeSectionManagerUpdate:
    """Tests for RecipeSectionManager.update()."""

    def test_update(self, recipe_section_manager, mock_client, sample_recipe_section):
        """Test updating a section."""
        mock_client._request.side_effect = [
            None,  # Update
            sample_recipe_section,  # Get updated
        ]

        result = recipe_section_manager.update(
            key=10,
            name="VM Settings",
            description="Updated description",
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "recipe_sections/10"
        body = update_call[1]["json_data"]
        assert body["name"] == "VM Settings"
        assert body["description"] == "Updated description"


class TestRecipeSectionManagerDelete:
    """Tests for RecipeSectionManager.delete()."""

    def test_delete(self, recipe_section_manager, mock_client):
        """Test deleting a section."""
        mock_client._request.return_value = None

        recipe_section_manager.delete(10)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "recipe_sections/10"


class TestRecipeSectionManagerQuestions:
    """Tests for RecipeSectionManager.questions()."""

    def test_get_questions_manager(self, recipe_section_manager, mock_client):
        """Test getting a scoped questions manager."""
        q_mgr = recipe_section_manager.questions(10)

        assert isinstance(q_mgr, RecipeQuestionManager)
        assert q_mgr._section_key == 10
