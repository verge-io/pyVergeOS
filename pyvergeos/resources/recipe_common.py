"""Recipe Questions and Sections shared between VM and Tenant recipes.

Recipe questions define the configuration options presented to users when deploying
a recipe. Questions are organized into sections that group related options together.

Question Types:
    User Input Types:
        - string: Free-form text input
        - number: Numeric value (supports min/max)
        - boolean: Checkbox (true/false)
        - password: Masked text with confirmation
        - list: Dropdown selection from predefined options
        - text_area: Multi-line text input
        - hidden: Not shown on form (for internal values)

    VergeOS-Specific Types:
        - ram: RAM selector with unit conversion
        - disk_size: Disk size selector
        - cluster: Cluster selection dropdown
        - network: Network selection dropdown
        - row_selection: Database row picker

    Database Automation Types:
        - database_create: Create a database record
        - database_edit: Modify a database record
        - database_find: Look up database values

Common Sections:
    - "Virtual Machine": Core VM settings (CPU, RAM, hostname)
    - "Network": Network and IP configuration
    - "Drives": Storage/disk settings
    - "Static IP Configuration": Manual IP settings
    - "User Configuration": Guest OS user accounts
    - "$database": Database automation (hidden from users)

Variable Naming Convention:
    Question names serve as variable names in recipe scripts. Common prefixes:
    - YB_* : VergeOS built-in variables (YB_RAM, YB_CPU_CORES, etc.)
    - SELECT_* : Selection/boolean options
    - Custom names for recipe-specific variables

Example:
    >>> # List questions for a recipe
    >>> recipe = client.vm_recipes.get(name="Ubuntu Server")
    >>> questions = client.recipe_questions.list(
    ...     recipe_ref=f"vm_recipes/{recipe.key}"
    ... )
    >>> for q in questions:
    ...     print(f"{q.name}: {q.question_type} - {q.get('display')}")

    >>> # Get sections for a recipe
    >>> sections = client.recipe_sections.list(
    ...     recipe_ref=f"vm_recipes/{recipe.key}"
    ... )
    >>> for s in sections:
    ...     print(f"{s.name}: {s.get('description', 'No description')}")
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class RecipeQuestion(ResourceObject):
    """Recipe question resource object.

    Represents a configuration question for a recipe. Questions are used
    to gather input during recipe deployment.

    Attributes:
        key: Question $key (integer row ID).
        recipe: Recipe reference (e.g., "vm_recipes/{id}" or "tenant_recipes/{id}").
        section: Section key this question belongs to.
        name: Question variable name (used in recipe scripts).
        display: Display label for the question.
        hint: Placeholder text shown in input field.
        help: Tooltip text shown on hover.
        note: Note text displayed below the field.
        type: Question type (string, bool, num, password, list, etc.).
        default: Default value for the question.
        required: Whether the question is required.
        enabled: Whether the question is enabled.
        readonly: Whether the question is read-only after creation.
        orderid: Display order within the section.
    """

    @property
    def recipe_ref(self) -> str | None:
        """Get the recipe reference string."""
        return self.get("recipe")

    @property
    def section_key(self) -> int | None:
        """Get the section key this question belongs to."""
        section = self.get("section")
        return int(section) if section is not None else None

    @property
    def question_type(self) -> str | None:
        """Get the question type."""
        return self.get("type")

    @property
    def is_required(self) -> bool:
        """Check if the question is required."""
        return bool(self.get("required", False))

    @property
    def is_enabled(self) -> bool:
        """Check if the question is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_readonly(self) -> bool:
        """Check if the question is read-only."""
        return bool(self.get("readonly", False))

    @property
    def is_password(self) -> bool:
        """Check if this is a password question."""
        return self.get("type") == "password"

    @property
    def is_hidden(self) -> bool:
        """Check if this is a hidden question."""
        return self.get("type") == "hidden"

    @property
    def list_options(self) -> dict[str, Any] | None:
        """Get list options if this is a list-type question."""
        if self.get("type") != "list":
            return None
        return self.get("list")


class RecipeSection(ResourceObject):
    """Recipe section resource object.

    Represents a section that groups related questions in a recipe form.

    Attributes:
        key: Section $key (integer row ID).
        recipe: Recipe reference (e.g., "vm_recipes/{id}" or "tenant_recipes/{id}").
        name: Section name.
        description: Section description.
        orderid: Display order.
    """

    @property
    def recipe_ref(self) -> str | None:
        """Get the recipe reference string."""
        return self.get("recipe")


class RecipeQuestionManager(ResourceManager["RecipeQuestion"]):
    """Manager for recipe question operations.

    Recipe questions define the configuration options available when deploying
    a recipe. Questions are organized into sections.

    Example:
        >>> # List all questions for a VM recipe
        >>> questions = client.recipe_questions.list(
        ...     recipe_ref="vm_recipes/8f73f8bcc9c9..."
        ... )
        >>> for q in questions:
        ...     print(f"{q.name}: {q.question_type} (required={q.is_required})")

        >>> # List questions for a specific section
        >>> questions = client.recipe_questions.list(section=123)
    """

    _endpoint = "recipe_questions"

    _default_fields = [
        "$key",
        "recipe",
        "section",
        "section#name as section_name",
        "name",
        "display",
        "hint",
        "help",
        "note",
        "type",
        "default",
        "required",
        "enabled",
        "readonly",
        "orderid",
        "min",
        "max",
        "regex",
        "list",
        "table",
        "fields",
        "filter",
        "database_context",
        "hide_none",
        "conditions",
        "on_change",
        "postprocess_string",
        "dont_store",
        "system",
    ]

    def __init__(
        self,
        client: VergeClient,
        *,
        recipe_ref: str | None = None,
        section_key: int | None = None,
    ) -> None:
        super().__init__(client)
        self._recipe_ref = recipe_ref
        self._section_key = section_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        recipe_ref: str | None = None,
        section: int | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[RecipeQuestion]:
        """List recipe questions with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            recipe_ref: Filter by recipe reference (e.g., "vm_recipes/{id}").
            section: Filter by section key.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, type, etc.).

        Returns:
            List of RecipeQuestion objects.

        Example:
            >>> # List all questions for a VM recipe
            >>> questions = client.recipe_questions.list(
            ...     recipe_ref="vm_recipes/8f73f8bcc9c9..."
            ... )

            >>> # List enabled questions only
            >>> enabled = client.recipe_questions.list(enabled=True)
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add recipe filter (from scope or parameter)
        recipe = self._recipe_ref
        if recipe is None and recipe_ref is not None:
            recipe = recipe_ref

        if recipe is not None:
            filters.append(f"recipe eq '{recipe}'")

        # Add section filter (from scope or parameter)
        sect = self._section_key
        if sect is None and section is not None:
            sect = section

        if sect is not None:
            filters.append(f"section eq {sect}")

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {1 if enabled else 0}")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Sort by orderid
        params["sort"] = "+orderid"

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> RecipeQuestion:
        """Get a single recipe question by key or name.

        Args:
            key: Question $key (row ID).
            name: Question name (variable name).
            fields: List of fields to return.

        Returns:
            RecipeQuestion object.

        Raises:
            NotFoundError: If question not found.
            ValueError: If no identifier provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Recipe question with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Recipe question with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Recipe question with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        recipe_ref: str,
        section: int,
        question_type: str,
        *,
        display: str | None = None,
        hint: str | None = None,
        help_text: str | None = None,
        note: str | None = None,
        default: str | None = None,
        required: bool = False,
        enabled: bool = True,
        readonly: bool = False,
        min_value: int | None = None,
        max_value: int | None = None,
        regex: str | None = None,
        list_options: dict[str, str] | None = None,
        table: str | None = None,
        fields: str | None = None,
        db_filter: str | None = None,
        database_context: str | None = None,
        hide_none: bool = False,
        conditions: dict[str, Any] | None = None,
        on_change: dict[str, Any] | None = None,
        postprocess_string: str | None = None,
        dont_store: bool = False,
    ) -> RecipeQuestion:
        """Create a new recipe question.

        Args:
            name: Variable name for the question (alphanumeric with underscores).
            recipe_ref: Recipe reference (e.g., "vm_recipes/{id}").
            section: Section key to add the question to.
            question_type: Question type (string, bool, num, password, list, etc.).
            display: Display label.
            hint: Placeholder text.
            help_text: Tooltip text.
            note: Note text below field.
            default: Default value.
            required: Whether the question is required.
            enabled: Whether the question is enabled.
            readonly: Whether the question is read-only after creation.
            min_value: Minimum value (for numeric types).
            max_value: Maximum value (for numeric types).
            regex: Validation regex.
            list_options: Options for list type (key: value dict).
            table: Database table for row selection type.
            fields: Database fields for row selection.
            db_filter: Database filter for row selection.
            database_context: Database context (local or tenant).
            hide_none: Hide the "None" option in lists.
            conditions: Conditional visibility rules.
            on_change: On-change actions.
            postprocess_string: Post-processing type.
            dont_store: Don't store the answer in the database.

        Returns:
            Created RecipeQuestion object.

        Example:
            >>> question = client.recipe_questions.create(
            ...     name="vm_ram",
            ...     recipe_ref="vm_recipes/8f73f8bcc9c9...",
            ...     section=123,
            ...     question_type="ram",
            ...     display="RAM",
            ...     default="4096",
            ...     required=True
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "recipe": recipe_ref,
            "section": section,
            "type": question_type,
        }

        if display is not None:
            body["display"] = display

        if hint is not None:
            body["hint"] = hint

        if help_text is not None:
            body["help"] = help_text

        if note is not None:
            body["note"] = note

        if default is not None:
            body["default"] = default

        body["required"] = required
        body["enabled"] = enabled
        body["readonly"] = readonly

        if min_value is not None:
            body["min"] = min_value

        if max_value is not None:
            body["max"] = max_value

        if regex is not None:
            body["regex"] = regex

        if list_options is not None:
            body["list"] = list_options

        if table is not None:
            body["table"] = table

        if fields is not None:
            body["fields"] = fields

        if db_filter is not None:
            body["filter"] = db_filter

        if database_context is not None:
            body["database_context"] = database_context

        body["hide_none"] = hide_none

        if conditions is not None:
            body["conditions"] = conditions

        if on_change is not None:
            body["on_change"] = on_change

        if postprocess_string is not None:
            body["postprocess_string"] = postprocess_string

        body["dont_store"] = dont_store

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created question
        if response and isinstance(response, dict):
            q_key = response.get("$key")
            if q_key:
                return self.get(key=q_key)

        # Fallback: search by name in the recipe
        results = self.list(
            recipe_ref=recipe_ref, filter=f"name eq '{name}'", limit=1
        )
        if results:
            return results[0]

        raise NotFoundError(f"Failed to retrieve created question '{name}'")

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        display: str | None = None,
        hint: str | None = None,
        help_text: str | None = None,
        note: str | None = None,
        default: str | None = None,
        required: bool | None = None,
        enabled: bool | None = None,
        readonly: bool | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        orderid: int | None = None,
    ) -> RecipeQuestion:
        """Update a recipe question.

        Args:
            key: Question $key (row ID).
            display: New display label.
            hint: New placeholder text.
            help_text: New tooltip text.
            note: New note text.
            default: New default value.
            required: Set required state.
            enabled: Set enabled state.
            readonly: Set readonly state.
            min_value: New minimum value.
            max_value: New maximum value.
            orderid: New display order.

        Returns:
            Updated RecipeQuestion object.
        """
        body: dict[str, Any] = {}

        if display is not None:
            body["display"] = display

        if hint is not None:
            body["hint"] = hint

        if help_text is not None:
            body["help"] = help_text

        if note is not None:
            body["note"] = note

        if default is not None:
            body["default"] = default

        if required is not None:
            body["required"] = required

        if enabled is not None:
            body["enabled"] = enabled

        if readonly is not None:
            body["readonly"] = readonly

        if min_value is not None:
            body["min"] = min_value

        if max_value is not None:
            body["max"] = max_value

        if orderid is not None:
            body["orderid"] = orderid

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a recipe question.

        Args:
            key: Question $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> RecipeQuestion:
        """Convert API response to RecipeQuestion object."""
        return RecipeQuestion(data, self)


class RecipeSectionManager(ResourceManager["RecipeSection"]):
    """Manager for recipe section operations.

    Recipe sections organize questions into logical groups.

    Example:
        >>> # List all sections for a VM recipe
        >>> sections = client.recipe_sections.list(
        ...     recipe_ref="vm_recipes/8f73f8bcc9c9..."
        ... )
        >>> for s in sections:
        ...     print(f"{s.name}: {s.description}")

        >>> # Create a new section
        >>> section = client.recipe_sections.create(
        ...     name="Network Settings",
        ...     recipe_ref="vm_recipes/8f73f8bcc9c9...",
        ...     description="Network configuration options"
        ... )
    """

    _endpoint = "recipe_sections"

    _default_fields = [
        "$key",
        "recipe",
        "name",
        "description",
        "orderid",
    ]

    def __init__(
        self,
        client: VergeClient,
        *,
        recipe_ref: str | None = None,
    ) -> None:
        super().__init__(client)
        self._recipe_ref = recipe_ref

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        recipe_ref: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[RecipeSection]:
        """List recipe sections with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            recipe_ref: Filter by recipe reference (e.g., "vm_recipes/{id}").
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of RecipeSection objects.

        Example:
            >>> # List all sections for a VM recipe
            >>> sections = client.recipe_sections.list(
            ...     recipe_ref="vm_recipes/8f73f8bcc9c9..."
            ... )
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add recipe filter (from scope or parameter)
        recipe = self._recipe_ref
        if recipe is None and recipe_ref is not None:
            recipe = recipe_ref

        if recipe is not None:
            filters.append(f"recipe eq '{recipe}'")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Sort by orderid
        params["sort"] = "+orderid"

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> RecipeSection:
        """Get a single recipe section by key or name.

        Args:
            key: Section $key (row ID).
            name: Section name.
            fields: List of fields to return.

        Returns:
            RecipeSection object.

        Raises:
            NotFoundError: If section not found.
            ValueError: If no identifier provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Recipe section with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Recipe section with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Recipe section with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        recipe_ref: str,
        *,
        description: str | None = None,
    ) -> RecipeSection:
        """Create a new recipe section.

        Args:
            name: Section name.
            recipe_ref: Recipe reference (e.g., "vm_recipes/{id}").
            description: Section description.

        Returns:
            Created RecipeSection object.

        Example:
            >>> section = client.recipe_sections.create(
            ...     name="Network Settings",
            ...     recipe_ref="vm_recipes/8f73f8bcc9c9...",
            ...     description="Network configuration options"
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "recipe": recipe_ref,
        }

        if description is not None:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created section
        if response and isinstance(response, dict):
            s_key = response.get("$key")
            if s_key:
                return self.get(key=s_key)

        # Fallback: search by name in the recipe
        results = self.list(
            recipe_ref=recipe_ref, filter=f"name eq '{name}'", limit=1
        )
        if results:
            return results[0]

        raise NotFoundError(f"Failed to retrieve created section '{name}'")

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        orderid: int | None = None,
    ) -> RecipeSection:
        """Update a recipe section.

        Args:
            key: Section $key (row ID).
            name: New name.
            description: New description.
            orderid: New display order.

        Returns:
            Updated RecipeSection object.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if orderid is not None:
            body["orderid"] = orderid

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a recipe section.

        Note: This will also delete all questions in the section.

        Args:
            key: Section $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def questions(self, key: int) -> RecipeQuestionManager:
        """Get a question manager scoped to a specific section.

        Args:
            key: Section $key (row ID).

        Returns:
            RecipeQuestionManager for the section.
        """
        return RecipeQuestionManager(self._client, section_key=key)

    def _to_model(self, data: dict[str, Any]) -> RecipeSection:
        """Convert API response to RecipeSection object."""
        return RecipeSection(data, self)
