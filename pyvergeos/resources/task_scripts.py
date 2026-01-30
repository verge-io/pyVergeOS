"""Task script resource manager for VergeOS automation scripts.

Task scripts are GCS (VergeOS scripting) code that can be executed as tasks.
Scripts can define questions (settings) that are prompted when running,
allowing for reusable automation with configurable parameters.

Example:
    >>> # List all scripts
    >>> for script in client.task_scripts.list():
    ...     print(f"{script.name}: {script.task_count} tasks")

    >>> # Create a simple script
    >>> script = client.task_scripts.create(
    ...     name="Cleanup Script",
    ...     description="Removes old temporary files",
    ...     script="# GCS script code here\\nlog('Cleanup started')",
    ...     task_settings={"questions": []},
    ... )

    >>> # Run a script
    >>> result = script.run()
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class TaskScript(ResourceObject):
    """Task script resource object.

    Represents a GCS automation script that can be executed as tasks.

    Properties:
        name: Script name (unique).
        description: Script description.
        script_code: The GCS script code.
        task_settings: JSON settings/questions for the script.
        task_count: Number of tasks using this script.
    """

    @property
    def script_code(self) -> str | None:
        """Get the script code."""
        return self.get("script")

    @property
    def settings(self) -> dict[str, Any] | None:
        """Get the script settings/questions."""
        settings = self.get("task_settings")
        if isinstance(settings, dict):
            return settings
        return None

    @property
    def task_count(self) -> int:
        """Get the number of tasks using this script."""
        return int(self.get("task_count", 0))

    def run(self, **params: Any) -> dict[str, Any] | None:
        """Run this script.

        Args:
            **params: Parameters to pass to the script.

        Returns:
            Run action response dict or None.
        """
        from typing import cast

        manager = cast("TaskScriptManager", self._manager)
        return manager.run(self.key, **params)


class TaskScriptManager(ResourceManager[TaskScript]):
    """Manager for task script operations.

    Task scripts provide reusable GCS automation code.

    Example:
        >>> # List all scripts
        >>> for script in client.task_scripts.list():
        ...     print(f"{script.name}: {script.description}")

        >>> # Create a script
        >>> script = client.task_scripts.create(
        ...     name="My Script",
        ...     script="log('Hello World')",
        ...     task_settings={"questions": []},
        ... )

        >>> # Get a script by name
        >>> script = client.task_scripts.get(name="My Script")

        >>> # Run a script
        >>> result = client.task_scripts.run(script.key)

        >>> # Update script code
        >>> script = client.task_scripts.update(
        ...     script.key,
        ...     script="log('Updated code')"
        ... )
    """

    _endpoint = "task_scripts"

    _default_fields = [
        "$key",
        "name",
        "description",
        "script",
        "task_settings",
        "count(tasks) as task_count",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> TaskScript:
        return TaskScript(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TaskScript]:
        """List task scripts with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            name: Filter by name.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of TaskScript objects.

        Example:
            >>> # All scripts
            >>> scripts = client.task_scripts.list()

            >>> # Scripts by name pattern
            >>> scripts = client.task_scripts.list(name="Backup*")
        """
        params: dict[str, Any] = {}

        # Build filter conditions
        filters: builtins.list[str] = []

        if filter:
            filters.append(f"({filter})")

        if name is not None:
            if "*" in name or "?" in name:
                search_term = name.replace("*", "").replace("?", "")
                if search_term:
                    filters.append(f"name ct '{search_term}'")
            else:
                escaped_name = name.replace("'", "''")
                filters.append(f"name eq '{escaped_name}'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TaskScript:
        """Get a task script by key or name.

        Args:
            key: Script $key (ID).
            name: Script name (unique).
            fields: List of fields to return.

        Returns:
            TaskScript object.

        Raises:
            NotFoundError: If script not found.
            ValueError: If neither key nor name provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Task script {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Task script {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Task script with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        script: str,
        *,
        description: str | None = None,
        task_settings: dict[str, Any] | None = None,
    ) -> TaskScript:
        """Create a new task script.

        Args:
            name: Script name (unique, required).
            script: GCS script code (required).
            description: Script description.
            task_settings: JSON settings/questions for the script.

        Returns:
            Created TaskScript object.

        Example:
            >>> script = client.task_scripts.create(
            ...     name="My Script",
            ...     description="Does something useful",
            ...     script="log('Hello World')",
            ...     task_settings={"questions": []},
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "script": script,
        }

        if description is not None:
            body["description"] = description

        if task_settings is not None:
            body["task_settings"] = task_settings
        else:
            # Provide default empty settings
            body["task_settings"] = {"questions": []}

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the full object
        key = response.get("$key")
        if key is not None:
            return self.get(int(key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        script: str | None = None,
        task_settings: dict[str, Any] | None = None,
    ) -> TaskScript:
        """Update an existing task script.

        Args:
            key: Script $key (ID).
            name: New name.
            description: New description.
            script: New GCS script code.
            task_settings: New settings/questions.

        Returns:
            Updated TaskScript object.

        Example:
            >>> script = client.task_scripts.update(
            ...     script.key,
            ...     script="log('Updated code')"
            ... )
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if script is not None:
            body["script"] = script
        if task_settings is not None:
            body["task_settings"] = task_settings

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a task script.

        Note:
            Scripts with associated tasks cannot be deleted.
            The tasks will be cascade deleted.

        Args:
            key: Script $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def run(self, key: int, **params: Any) -> dict[str, Any] | None:
        """Run a task script.

        Executes the script, optionally with provided parameters.

        Args:
            key: Script $key (ID).
            **params: Parameters to pass to the script.

        Returns:
            Run action response dict or None.

        Example:
            >>> # Run a script
            >>> result = client.task_scripts.run(script.key)

            >>> # Run with parameters
            >>> result = client.task_scripts.run(
            ...     script.key,
            ...     target_vm=123,
            ...     cleanup=True,
            ... )
        """
        return self.action(key, "run", **params)
