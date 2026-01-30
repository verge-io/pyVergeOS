"""VM Recipe resources for VergeOS provisioning system.

VM recipes are customizable templates for deploying virtual machines. They consist
of a golden image (base VM) and configurable options via questions that allow
users to customize each deployment.

Key concepts:
    - **Recipe**: A template based on a golden image VM, stored in a catalog
    - **Instance**: A VM created from a recipe (remains linked until detached)
    - **Questions**: Configuration inputs grouped into sections
    - **Sections**: Logical groups like "Virtual Machine", "Network", "Drives"

Common question variable names:
    - YB_CPU_CORES: Number of CPU cores
    - YB_RAM: RAM amount in MB
    - YB_HOSTNAME: VM hostname
    - YB_IP_ADDR_TYPE: IP type (dhcp/static)
    - YB_NIC_ETH0: Network selection for eth0
    - YB_DRIVE_OS_SIZE: OS disk size in bytes
    - YB_USER: Username for guest OS
    - YB_PASSWORD: Password for guest OS
    - OS_DL_URL: Cloud image download URL (for cloud-init images)

Question types:
    - string, number, boolean, password, list, hidden
    - ram, cluster, network, disk_size, row_selection, text_area
    - database_create, database_edit, database_find (for API automation)

Example:
    >>> # List available recipes
    >>> for recipe in client.vm_recipes.list(downloaded=True):
    ...     print(f"{recipe.name} (v{recipe.version})")

    >>> # Deploy a recipe
    >>> recipe = client.vm_recipes.get(name="Ubuntu Server 22.04")
    >>> instance = recipe.deploy("my-ubuntu", answers={
    ...     "YB_CPU_CORES": 4,
    ...     "YB_RAM": 8192,
    ...     "YB_HOSTNAME": "my-ubuntu-server",
    ...     "YB_IP_ADDR_TYPE": "dhcp",
    ... })
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class VmRecipe(ResourceObject):
    """VM Recipe resource object.

    Represents a VM recipe template that can be deployed to create new VMs.

    Note:
        Recipe keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The recipe unique identifier ($key) - 40-char hex string.
        id: The recipe ID (same as $key).
        name: Recipe name.
        description: Recipe description.
        version: Recipe version string.
        build: Recipe build number.
        icon: Bootstrap icon name for UI display.
        catalog: Parent catalog key.
        status: Recipe status row key.
        downloaded: Whether the recipe has been downloaded.
        update_available: Whether an update is available.
        needs_republish: Whether the recipe needs republishing.
        vm: Associated VM key (for local recipes).
        vm_snapshot: Associated VM snapshot key.
        creator: Username who created the recipe.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - 40-character hex string.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> VmRecipe:
        """Refresh resource data from API.

        Returns:
            Updated VmRecipe object.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> VmRecipe:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated VmRecipe object.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this recipe."""
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        manager.delete(self.key)

    @property
    def is_downloaded(self) -> bool:
        """Check if the recipe has been downloaded."""
        return bool(self.get("downloaded", False))

    @property
    def has_update(self) -> bool:
        """Check if an update is available."""
        return bool(self.get("update_available", False))

    @property
    def status_info(self) -> str | None:
        """Get the recipe status string."""
        return self.get("status") or self.get("rstatus")

    @property
    def catalog_key(self) -> str | None:
        """Get the parent catalog key."""
        cat = self.get("catalog")
        return str(cat) if cat is not None else None

    @property
    def vm_key(self) -> int | None:
        """Get the associated VM key."""
        vm = self.get("vm")
        return int(vm) if vm is not None else None

    @property
    def instance_count(self) -> int:
        """Get the number of deployed instances."""
        return int(self.get("instances", 0))

    @property
    def instances(self) -> VmRecipeInstanceManager:
        """Get an instance manager scoped to this recipe.

        Returns:
            VmRecipeInstanceManager for this recipe.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return VmRecipeInstanceManager(manager._client, recipe_key=self.key)

    @property
    def logs(self) -> VmRecipeLogManager:
        """Get a log manager scoped to this recipe.

        Returns:
            VmRecipeLogManager for this recipe.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return VmRecipeLogManager(manager._client, recipe_key=self.key)

    def download(self) -> dict[str, Any] | None:
        """Download this recipe from the catalog repository.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return manager.download(self.key)

    def deploy(
        self,
        name: str,
        *,
        answers: dict[str, Any] | None = None,
        auto_update: bool = False,
    ) -> VmRecipeInstance:
        """Deploy this recipe to create a new VM.

        Args:
            name: Name for the new VM.
            answers: Recipe question answers.
            auto_update: Auto-update when recipe updates are available.

        Returns:
            Created VmRecipeInstance object.
        """
        from typing import cast

        manager = cast("VmRecipeManager", self._manager)
        return manager.deploy(
            self.key, name=name, answers=answers, auto_update=auto_update
        )


class VmRecipeInstance(ResourceObject):
    """VM Recipe instance resource object.

    Represents a deployed instance of a VM recipe.

    Attributes:
        key: Instance $key (integer row ID).
        recipe: Recipe key that this instance was deployed from.
        vm: VM key that was created.
        name: Instance/VM name.
        version: Recipe version when deployed.
        build: Recipe build when deployed.
        answers: Recipe question answers used.
        auto_update: Whether auto-update is enabled.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def recipe_key(self) -> str | None:
        """Get the recipe key this instance was deployed from."""
        recipe = self.get("recipe")
        return str(recipe) if recipe is not None else None

    @property
    def vm_key(self) -> int | None:
        """Get the VM key that was created."""
        vm = self.get("vm")
        return int(vm) if vm is not None else None

    @property
    def is_auto_update(self) -> bool:
        """Check if auto-update is enabled."""
        return bool(self.get("auto_update", False))


class VmRecipeLog(ResourceObject):
    """VM Recipe log entry resource object.

    Represents a log entry from recipe operations.

    Attributes:
        key: Log entry $key (integer row ID).
        vm_recipe: Recipe key.
        level: Log level (message, warning, error, critical, etc.).
        text: Log message text.
        timestamp: Log timestamp (microseconds).
        user: User who triggered the log.
    """

    @property
    def recipe_key(self) -> str | None:
        """Get the recipe key."""
        recipe = self.get("vm_recipe")
        return str(recipe) if recipe is not None else None

    @property
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        level = self.get("level", "")
        return level in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.get("level") == "warning"


class VmRecipeManager(ResourceManager["VmRecipe"]):
    """Manager for VM recipe operations.

    VM recipes are templates for automated VM provisioning.

    Example:
        >>> # List all recipes
        >>> for recipe in client.vm_recipes.list():
        ...     print(f"{recipe.name}: {recipe.version}")

        >>> # Get a specific recipe
        >>> recipe = client.vm_recipes.get(name="Ubuntu Server")

        >>> # Deploy a recipe
        >>> instance = recipe.deploy("my-ubuntu", answers={"ram": 4096})
    """

    _endpoint = "vm_recipes"

    _default_fields = [
        "$key",
        "id",
        "name",
        "description",
        "icon",
        "version",
        "build",
        "catalog",
        "catalog#$display as catalog_display",
        "catalog#repository as catalog_repository",
        "catalog#repository#$display as repository_display",
        "status#status as status",
        "status#status as rstatus",
        "downloaded",
        "update_available",
        "needs_republish",
        "vm",
        "vm#$display as vm_display",
        "vm_snapshot",
        "vm_snapshot#$display as snapshot_display",
        "count(instances) as instances",
        "creator",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        catalog: str | int | None = None,
        downloaded: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmRecipe]:
        """List VM recipes with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            catalog: Filter by catalog (key or name).
            downloaded: Filter by downloaded state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of VmRecipe objects.

        Example:
            >>> # List all recipes
            >>> recipes = client.vm_recipes.list()

            >>> # List downloaded recipes only
            >>> downloaded = client.vm_recipes.list(downloaded=True)

            >>> # Filter by name
            >>> ubuntu = client.vm_recipes.list(name="Ubuntu*")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add catalog filter
        if catalog is not None:
            if isinstance(catalog, int):
                filters.append(f"catalog eq {catalog}")
            elif isinstance(catalog, str):
                # Check if it looks like a catalog key (40-char hex) or a name
                if len(catalog) == 40 and all(
                    c in "0123456789abcdef" for c in catalog.lower()
                ):
                    filters.append(f"catalog eq '{catalog}'")
                else:
                    # Look up catalog by name
                    cat_response = self._client._request(
                        "GET",
                        "catalogs",
                        params={
                            "filter": f"name eq '{catalog}'",
                            "fields": "$key",
                            "limit": "1",
                        },
                    )
                    if cat_response:
                        if isinstance(cat_response, list):
                            cat_response = cat_response[0] if cat_response else None
                        if cat_response:
                            filters.append(f"catalog eq '{cat_response.get('$key')}'")

        # Add downloaded filter
        if downloaded is not None:
            filters.append(f"downloaded eq {1 if downloaded else 0}")

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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: str | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VmRecipe:
        """Get a single VM recipe by key or name.

        Args:
            key: Recipe $key (40-character hex string).
            name: Recipe name.
            fields: List of fields to return.

        Returns:
            VmRecipe object.

        Raises:
            NotFoundError: If recipe not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> recipe = client.vm_recipes.get("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

            >>> # Get by name
            >>> recipe = client.vm_recipes.get(name="Ubuntu Server")
        """
        if key is not None:
            # Fetch by key using id filter
            params: dict[str, Any] = {
                "filter": f"id eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"VM recipe with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"VM recipe with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"VM recipe with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"VM recipe with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        version: str | None = None,
    ) -> VmRecipe:
        """Update a VM recipe.

        Args:
            key: Recipe $key (40-character hex string).
            name: New name.
            description: New description.
            icon: New icon name.
            version: New version string.

        Returns:
            Updated VmRecipe object.

        Example:
            >>> client.vm_recipes.update(recipe.key, description="Updated description")
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if icon is not None:
            body["icon"] = icon

        if version is not None:
            body["version"] = version

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a VM recipe.

        This operation is destructive and cannot be undone.

        Args:
            key: Recipe $key (40-character hex string).

        Raises:
            NotFoundError: If recipe not found.

        Example:
            >>> client.vm_recipes.delete(recipe.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def download(self, key: str) -> dict[str, Any] | None:
        """Download a recipe from the catalog repository.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            Task information dict or None.

        Example:
            >>> client.vm_recipes.download(recipe.key)
        """
        result = self._client._request(
            "PUT", f"{self._endpoint}/{key}?action=download", json_data={}
        )
        if isinstance(result, dict):
            return result
        return None

    def deploy(
        self,
        key: str,
        name: str,
        *,
        answers: dict[str, Any] | None = None,
        auto_update: bool = False,
    ) -> VmRecipeInstance:
        """Deploy a recipe to create a new VM.

        Args:
            key: Recipe $key (40-character hex string).
            name: Name for the new VM.
            answers: Recipe question answers.
            auto_update: Auto-update when recipe updates are available.

        Returns:
            Created VmRecipeInstance object.

        Example:
            >>> instance = client.vm_recipes.deploy(
            ...     recipe.key,
            ...     "my-vm",
            ...     answers={"ram": 4096, "cpu_cores": 2}
            ... )
        """
        instance_mgr = VmRecipeInstanceManager(self._client)
        return instance_mgr.create(
            recipe=key, name=name, answers=answers, auto_update=auto_update
        )

    def instances(self, key: str) -> VmRecipeInstanceManager:
        """Get an instance manager scoped to a specific recipe.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            VmRecipeInstanceManager for the recipe.
        """
        return VmRecipeInstanceManager(self._client, recipe_key=key)

    def logs(self, key: str) -> VmRecipeLogManager:
        """Get a log manager scoped to a specific recipe.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            VmRecipeLogManager for the recipe.
        """
        return VmRecipeLogManager(self._client, recipe_key=key)

    def _to_model(self, data: dict[str, Any]) -> VmRecipe:
        """Convert API response to VmRecipe object."""
        return VmRecipe(data, self)


class VmRecipeInstanceManager(ResourceManager["VmRecipeInstance"]):
    """Manager for VM recipe instance operations.

    Recipe instances represent deployed VMs created from recipes.

    Example:
        >>> # List all instances
        >>> for inst in client.vm_recipe_instances.list():
        ...     print(f"{inst.name}: {inst.version}")

        >>> # List instances for a specific recipe
        >>> for inst in client.vm_recipes.get(name="Ubuntu").instances.list():
        ...     print(inst.name)
    """

    _endpoint = "vm_recipe_instances"

    _default_fields = [
        "$key",
        "recipe",
        "recipe#$display as recipe_display",
        "recipe#name as recipe_name",
        "vm",
        "vm#$display as vm_display",
        "vm#name as vm_name",
        "name",
        "version",
        "build",
        "auto_update",
        "created",
        "modified",
    ]

    def __init__(
        self, client: VergeClient, *, recipe_key: str | None = None
    ) -> None:
        super().__init__(client)
        self._recipe_key = recipe_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        recipe: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmRecipeInstance]:
        """List recipe instances with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            recipe: Filter by recipe key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of VmRecipeInstance objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add recipe filter (from scope or parameter)
        recipe_key = self._recipe_key
        if recipe_key is None and recipe is not None:
            recipe_key = recipe

        if recipe_key is not None:
            filters.append(f"recipe eq '{recipe_key}'")

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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VmRecipeInstance:
        """Get a single recipe instance by key or name.

        Args:
            key: Instance $key (row ID).
            name: Instance/VM name.
            fields: List of fields to return.

        Returns:
            VmRecipeInstance object.

        Raises:
            NotFoundError: If instance not found.
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
                raise NotFoundError(f"Recipe instance with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Recipe instance with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Recipe instance with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        recipe: str,
        name: str,
        *,
        answers: dict[str, Any] | None = None,
        auto_update: bool = False,
    ) -> VmRecipeInstance:
        """Create a new recipe instance (deploy a recipe).

        Args:
            recipe: Recipe $key (40-character hex string).
            name: Name for the new VM.
            answers: Recipe question answers.
            auto_update: Auto-update when recipe updates are available.

        Returns:
            Created VmRecipeInstance object.

        Example:
            >>> instance = client.vm_recipe_instances.create(
            ...     recipe="8f73f8bcc9c9...",
            ...     name="my-vm",
            ...     answers={"ram": 4096}
            ... )
        """
        body: dict[str, Any] = {
            "recipe": recipe,
            "name": name,
        }

        if answers is not None:
            body["answers"] = answers

        if auto_update:
            body["auto_update"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created instance
        if response and isinstance(response, dict):
            inst_key = response.get("$key")
            if inst_key:
                return self.get(key=inst_key)

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        auto_update: bool | None = None,
        answers: dict[str, Any] | None = None,
    ) -> VmRecipeInstance:
        """Update a recipe instance.

        Args:
            key: Instance $key (row ID).
            auto_update: Enable or disable auto-update.
            answers: Update recipe answers.

        Returns:
            Updated VmRecipeInstance object.
        """
        body: dict[str, Any] = {}

        if auto_update is not None:
            body["auto_update"] = auto_update

        if answers is not None:
            body["answers"] = answers

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a recipe instance.

        Note: This typically does NOT delete the created VM.

        Args:
            key: Instance $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> VmRecipeInstance:
        """Convert API response to VmRecipeInstance object."""
        return VmRecipeInstance(data, self)


class VmRecipeLogManager(ResourceManager["VmRecipeLog"]):
    """Manager for VM recipe log operations.

    Example:
        >>> # List all recipe logs
        >>> for log in client.vm_recipe_logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List logs for a specific recipe
        >>> for log in client.vm_recipes.get(name="Ubuntu").logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "vm_recipe_logs"

    _default_fields = [
        "$key",
        "vm_recipe",
        "vm_recipe#name as vm_recipe_display",
        "level",
        "text",
        "timestamp",
        "user",
    ]

    def __init__(
        self, client: VergeClient, *, recipe_key: str | None = None
    ) -> None:
        super().__init__(client)
        self._recipe_key = recipe_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        vm_recipe: str | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmRecipeLog]:
        """List recipe logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            vm_recipe: Filter by recipe key. Ignored if manager is scoped.
            level: Filter by log level.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VmRecipeLog objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add recipe filter (from scope or parameter)
        recipe_key = self._recipe_key
        if recipe_key is None and vm_recipe is not None:
            recipe_key = vm_recipe

        if recipe_key is not None:
            filters.append(f"vm_recipe eq '{recipe_key}'")

        # Add level filter
        if level is not None:
            filters.append(f"level eq '{level}'")

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

        # Default sort by timestamp descending
        params["sort"] = "-timestamp"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> VmRecipeLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            VmRecipeLog object.

        Raises:
            NotFoundError: If log entry not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request(
            "GET", f"{self._endpoint}/{key}", params=params
        )
        if response is None:
            raise NotFoundError(f"Recipe log with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Recipe log with key {key} returned invalid response")
        return self._to_model(response)

    def list_errors(
        self,
        limit: int | None = None,
    ) -> builtins.list[VmRecipeLog]:
        """List error and critical log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of error/critical log entries.
        """
        return self.list(
            filter="(level eq 'error') or (level eq 'critical')",
            limit=limit,
        )

    def list_warnings(
        self,
        limit: int | None = None,
    ) -> builtins.list[VmRecipeLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> VmRecipeLog:
        """Convert API response to VmRecipeLog object."""
        return VmRecipeLog(data, self)
