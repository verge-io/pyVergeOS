"""Tenant Recipe resources for VergeOS provisioning system.

Tenant recipes enable automated deployment of complete virtual data centers.
A tenant recipe includes everything needed to spawn a functional tenant instance:
tenant settings, networking configuration, VMs, and automation for tasks like
creating passwords, establishing hostnames, registering DNS entries, etc.

Key concepts:
    - **Recipe**: A template based on a powered-off tenant, stored in a catalog
    - **Instance**: A tenant created from a recipe (remains linked until detached)
    - **Questions**: Configuration inputs for customizing each tenant deployment
    - **Sections**: Logical groups organizing questions on the deployment form

Benefits:
    - Rapid deployment of entire tenants with consistent configurations
    - Golden images for compliance and standardization
    - Reduced manual setup time and human error
    - Customizable via questions for tenant-specific settings

Database Context:
    Tenant recipe questions can interact with either the parent system database
    or the newly-created tenant's database using the database_context field.
    This enables powerful automation like creating users, registering DNS, etc.

Example:
    >>> # List available tenant recipes
    >>> for recipe in client.tenant_recipes.list(downloaded=True):
    ...     print(f"{recipe.name} (v{recipe.version})")

    >>> # Deploy a tenant recipe
    >>> recipe = client.tenant_recipes.get(name="30-Day Trial (POC)")
    >>> instance = recipe.deploy("customer-tenant", answers={
    ...     "TENANT_NAME": "Acme Corp",
    ...     "ADMIN_USER": "admin",
    ...     "ADMIN_PASSWORD": "secure-password",
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


class TenantRecipe(ResourceObject):
    """Tenant Recipe resource object.

    Represents a tenant recipe template that can be deployed to create new tenants.

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
        tenant: Associated tenant key (for local recipes).
        tenant_snapshot: Associated tenant snapshot key.
        preserve_certs: Whether to preserve SSL certificates during deployment.
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

    def refresh(self) -> TenantRecipe:
        """Refresh resource data from API.

        Returns:
            Updated TenantRecipe object.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> TenantRecipe:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated TenantRecipe object.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this recipe."""
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
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
    def tenant_key(self) -> int | None:
        """Get the associated tenant key."""
        tenant = self.get("tenant")
        return int(tenant) if tenant is not None else None

    @property
    def instance_count(self) -> int:
        """Get the number of deployed instances."""
        return int(self.get("instances", 0))

    @property
    def instances(self) -> TenantRecipeInstanceManager:
        """Get an instance manager scoped to this recipe.

        Returns:
            TenantRecipeInstanceManager for this recipe.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return TenantRecipeInstanceManager(manager._client, recipe_key=self.key)

    @property
    def logs(self) -> TenantRecipeLogManager:
        """Get a log manager scoped to this recipe.

        Returns:
            TenantRecipeLogManager for this recipe.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return TenantRecipeLogManager(manager._client, recipe_key=self.key)

    def download(self) -> dict[str, Any] | None:
        """Download this recipe from the catalog repository.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return manager.download(self.key)

    def deploy(
        self,
        name: str,
        *,
        answers: dict[str, Any] | None = None,
    ) -> TenantRecipeInstance:
        """Deploy this recipe to create a new tenant.

        Args:
            name: Name for the new tenant.
            answers: Recipe question answers.

        Returns:
            Created TenantRecipeInstance object.
        """
        from typing import cast

        manager = cast("TenantRecipeManager", self._manager)
        return manager.deploy(self.key, name=name, answers=answers)


class TenantRecipeInstance(ResourceObject):
    """Tenant Recipe instance resource object.

    Represents a deployed instance of a tenant recipe.

    Attributes:
        key: Instance $key (integer row ID).
        recipe: Recipe key that this instance was deployed from.
        tenant: Tenant key that was created.
        name: Instance/tenant name.
        version: Recipe version when deployed.
        build: Recipe build when deployed.
        answers: Recipe question answers used.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def recipe_key(self) -> str | None:
        """Get the recipe key this instance was deployed from."""
        recipe = self.get("recipe")
        return str(recipe) if recipe is not None else None

    @property
    def tenant_key(self) -> int | None:
        """Get the tenant key that was created."""
        tenant = self.get("tenant")
        return int(tenant) if tenant is not None else None


class TenantRecipeLog(ResourceObject):
    """Tenant Recipe log entry resource object.

    Represents a log entry from recipe operations.

    Attributes:
        key: Log entry $key (integer row ID).
        tenant_recipe: Recipe key.
        level: Log level (message, warning, error, critical, etc.).
        text: Log message text.
        timestamp: Log timestamp (microseconds).
        user: User who triggered the log.
    """

    @property
    def recipe_key(self) -> str | None:
        """Get the recipe key."""
        recipe = self.get("tenant_recipe")
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


class TenantRecipeManager(ResourceManager["TenantRecipe"]):
    """Manager for tenant recipe operations.

    Tenant recipes are templates for automated tenant provisioning.

    Example:
        >>> # List all recipes
        >>> for recipe in client.tenant_recipes.list():
        ...     print(f"{recipe.name}: {recipe.version}")

        >>> # Get a specific recipe
        >>> recipe = client.tenant_recipes.get(name="Standard Tenant")

        >>> # Deploy a recipe
        >>> instance = recipe.deploy("my-tenant", answers={"storage_gb": 500})
    """

    _endpoint = "tenant_recipes"

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
        "preserve_certs",
        "tenant",
        "tenant#$display as tenant_display",
        "tenant_snapshot",
        "tenant_snapshot#$display as snapshot_display",
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
    ) -> builtins.list[TenantRecipe]:
        """List tenant recipes with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            catalog: Filter by catalog (key or name).
            downloaded: Filter by downloaded state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of TenantRecipe objects.

        Example:
            >>> # List all recipes
            >>> recipes = client.tenant_recipes.list()

            >>> # List downloaded recipes only
            >>> downloaded = client.tenant_recipes.list(downloaded=True)

            >>> # Filter by name
            >>> standard = client.tenant_recipes.list(name="Standard*")
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
    ) -> TenantRecipe:
        """Get a single tenant recipe by key or name.

        Args:
            key: Recipe $key (40-character hex string).
            name: Recipe name.
            fields: List of fields to return.

        Returns:
            TenantRecipe object.

        Raises:
            NotFoundError: If recipe not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> recipe = client.tenant_recipes.get("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

            >>> # Get by name
            >>> recipe = client.tenant_recipes.get(name="Standard Tenant")
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
                raise NotFoundError(f"Tenant recipe with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Tenant recipe with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Tenant recipe with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Tenant recipe with name '{name}' not found")
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
        preserve_certs: bool | None = None,
    ) -> TenantRecipe:
        """Update a tenant recipe.

        Args:
            key: Recipe $key (40-character hex string).
            name: New name.
            description: New description.
            icon: New icon name.
            version: New version string.
            preserve_certs: Whether to preserve SSL certs during deployment.

        Returns:
            Updated TenantRecipe object.

        Example:
            >>> client.tenant_recipes.update(recipe.key, description="Updated description")
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

        if preserve_certs is not None:
            body["preserve_certs"] = preserve_certs

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a tenant recipe.

        This operation is destructive and cannot be undone.

        Args:
            key: Recipe $key (40-character hex string).

        Raises:
            NotFoundError: If recipe not found.

        Example:
            >>> client.tenant_recipes.delete(recipe.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def download(self, key: str) -> dict[str, Any] | None:
        """Download a recipe from the catalog repository.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            Task information dict or None.

        Example:
            >>> client.tenant_recipes.download(recipe.key)
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
    ) -> TenantRecipeInstance:
        """Deploy a recipe to create a new tenant.

        Args:
            key: Recipe $key (40-character hex string).
            name: Name for the new tenant.
            answers: Recipe question answers.

        Returns:
            Created TenantRecipeInstance object.

        Example:
            >>> instance = client.tenant_recipes.deploy(
            ...     recipe.key,
            ...     "my-tenant",
            ...     answers={"storage_gb": 500, "cpu_cores": 4}
            ... )
        """
        instance_mgr = TenantRecipeInstanceManager(self._client)
        return instance_mgr.create(recipe=key, name=name, answers=answers)

    def instances(self, key: str) -> TenantRecipeInstanceManager:
        """Get an instance manager scoped to a specific recipe.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            TenantRecipeInstanceManager for the recipe.
        """
        return TenantRecipeInstanceManager(self._client, recipe_key=key)

    def logs(self, key: str) -> TenantRecipeLogManager:
        """Get a log manager scoped to a specific recipe.

        Args:
            key: Recipe $key (40-character hex string).

        Returns:
            TenantRecipeLogManager for the recipe.
        """
        return TenantRecipeLogManager(self._client, recipe_key=key)

    def _to_model(self, data: dict[str, Any]) -> TenantRecipe:
        """Convert API response to TenantRecipe object."""
        return TenantRecipe(data, self)


class TenantRecipeInstanceManager(ResourceManager["TenantRecipeInstance"]):
    """Manager for tenant recipe instance operations.

    Recipe instances represent deployed tenants created from recipes.

    Example:
        >>> # List all instances
        >>> for inst in client.tenant_recipe_instances.list():
        ...     print(f"{inst.name}: {inst.version}")

        >>> # List instances for a specific recipe
        >>> for inst in client.tenant_recipes.get(name="Standard").instances.list():
        ...     print(inst.name)
    """

    _endpoint = "tenant_recipe_instances"

    _default_fields = [
        "$key",
        "recipe",
        "recipe#$display as recipe_display",
        "recipe#name as recipe_name",
        "tenant",
        "tenant#$display as tenant_display",
        "tenant#name as tenant_name",
        "name",
        "version",
        "build",
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
    ) -> builtins.list[TenantRecipeInstance]:
        """List recipe instances with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            recipe: Filter by recipe key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of TenantRecipeInstance objects.
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
    ) -> TenantRecipeInstance:
        """Get a single recipe instance by key or name.

        Args:
            key: Instance $key (row ID).
            name: Instance/tenant name.
            fields: List of fields to return.

        Returns:
            TenantRecipeInstance object.

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
    ) -> TenantRecipeInstance:
        """Create a new recipe instance (deploy a recipe).

        Args:
            recipe: Recipe $key (40-character hex string).
            name: Name for the new tenant.
            answers: Recipe question answers.

        Returns:
            Created TenantRecipeInstance object.

        Example:
            >>> instance = client.tenant_recipe_instances.create(
            ...     recipe="8f73f8bcc9c9...",
            ...     name="my-tenant",
            ...     answers={"storage_gb": 500}
            ... )
        """
        body: dict[str, Any] = {
            "recipe": recipe,
            "name": name,
        }

        if answers is not None:
            body["answers"] = answers

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created instance
        if response and isinstance(response, dict):
            inst_key = response.get("$key")
            if inst_key:
                return self.get(key=inst_key)

        # Fallback: search by name
        return self.get(name=name)

    def delete(self, key: int) -> None:
        """Delete a recipe instance.

        Note: This typically does NOT delete the created tenant.

        Args:
            key: Instance $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> TenantRecipeInstance:
        """Convert API response to TenantRecipeInstance object."""
        return TenantRecipeInstance(data, self)


class TenantRecipeLogManager(ResourceManager["TenantRecipeLog"]):
    """Manager for tenant recipe log operations.

    Example:
        >>> # List all recipe logs
        >>> for log in client.tenant_recipe_logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List logs for a specific recipe
        >>> for log in client.tenant_recipes.get(name="Standard").logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "tenant_recipe_logs"

    _default_fields = [
        "$key",
        "tenant_recipe",
        "tenant_recipe#name as tenant_recipe_display",
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
        tenant_recipe: str | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TenantRecipeLog]:
        """List recipe logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            tenant_recipe: Filter by recipe key. Ignored if manager is scoped.
            level: Filter by log level.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of TenantRecipeLog objects.
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
        if recipe_key is None and tenant_recipe is not None:
            recipe_key = tenant_recipe

        if recipe_key is not None:
            filters.append(f"tenant_recipe eq '{recipe_key}'")

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
    ) -> TenantRecipeLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            TenantRecipeLog object.

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
    ) -> builtins.list[TenantRecipeLog]:
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
    ) -> builtins.list[TenantRecipeLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> TenantRecipeLog:
        """Convert API response to TenantRecipeLog object."""
        return TenantRecipeLog(data, self)
