"""Integration tests for ResourceGroup operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.

Note: Resource groups are read-only and configured through the VergeOS UI.
These tests only verify list and get operations.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.resource_groups import (
    DEVICE_CLASS_MAP,
    DEVICE_TYPE_MAP,
    ResourceGroup,
)


@pytest.mark.integration
class TestResourceGroupListIntegration:
    """Integration tests for ResourceGroupManager list operations."""

    def test_list_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing resource groups from live system."""
        groups = live_client.resource_groups.list()

        # Should return a list (may be empty if no resource groups configured)
        assert isinstance(groups, list)

        # Each group should have expected properties
        for group in groups:
            assert isinstance(group, ResourceGroup)
            assert hasattr(group, "key")
            assert hasattr(group, "uuid")
            assert hasattr(group, "name")
            assert hasattr(group, "device_type")
            assert hasattr(group, "device_type_display")
            assert hasattr(group, "device_class")
            assert hasattr(group, "device_class_display")
            assert hasattr(group, "is_enabled")
            assert hasattr(group, "resource_count")

    def test_list_resource_groups_with_limit(self, live_client: VergeClient) -> None:
        """Test listing resource groups with limit."""
        groups = live_client.resource_groups.list(limit=1)

        assert isinstance(groups, list)
        assert len(groups) <= 1

    def test_list_enabled_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing enabled resource groups."""
        groups = live_client.resource_groups.list_enabled()

        assert isinstance(groups, list)
        for group in groups:
            assert group.is_enabled is True

    def test_list_disabled_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing disabled resource groups."""
        groups = live_client.resource_groups.list_disabled()

        assert isinstance(groups, list)
        for group in groups:
            assert group.is_enabled is False


@pytest.mark.integration
class TestResourceGroupGetIntegration:
    """Integration tests for ResourceGroupManager get operations."""

    def test_get_resource_group_by_key(self, live_client: VergeClient) -> None:
        """Test getting a resource group by key."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(group.key)

        assert fetched.key == group.key
        assert fetched.name == group.name
        assert fetched.uuid == group.uuid

    def test_get_resource_group_by_name(self, live_client: VergeClient) -> None:
        """Test getting a resource group by name."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(name=group.name)

        assert fetched.key == group.key
        assert fetched.name == group.name

    def test_get_resource_group_by_uuid(self, live_client: VergeClient) -> None:
        """Test getting a resource group by UUID."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(uuid=group.uuid)

        assert fetched.key == group.key
        assert fetched.uuid == group.uuid

    def test_get_resource_group_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent resource group."""
        with pytest.raises(NotFoundError):
            live_client.resource_groups.get(name="non-existent-resource-group-12345")


@pytest.mark.integration
class TestResourceGroupFilterIntegration:
    """Integration tests for ResourceGroupManager filter operations."""

    def test_list_by_type(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device type."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a type from existing groups
        device_type = groups[0].device_type

        # Filter by that type
        filtered = live_client.resource_groups.list_by_type(device_type)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type == device_type

    def test_list_by_type_with_display_name(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device type display name."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a display name from existing groups
        device_type_display = groups[0].device_type_display

        # Filter by that display name
        filtered = live_client.resource_groups.list_by_type(device_type_display)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type_display == device_type_display

    def test_list_by_class(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device class."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a class from existing groups
        device_class = groups[0].device_class

        # Filter by that class
        filtered = live_client.resource_groups.list_by_class(device_class)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_class == device_class

    def test_list_by_type_with_enabled_filter(self, live_client: VergeClient) -> None:
        """Test listing resource groups by type with enabled filter."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a type from existing groups
        device_type = groups[0].device_type

        # Filter by type and enabled
        filtered = live_client.resource_groups.list_by_type(device_type, enabled=True)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type == device_type
            assert group.is_enabled is True

    def test_list_by_class_with_enabled_filter(self, live_client: VergeClient) -> None:
        """Test listing resource groups by class with enabled filter."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a class from existing groups
        device_class = groups[0].device_class

        # Filter by class and enabled
        filtered = live_client.resource_groups.list_by_class(device_class, enabled=True)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_class == device_class
            assert group.is_enabled is True


@pytest.mark.integration
class TestResourceGroupPropertiesIntegration:
    """Integration tests for ResourceGroup properties."""

    def test_resource_group_properties(self, live_client: VergeClient) -> None:
        """Test that resource group properties are correctly populated."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]

        # Test all property accessors work without error
        assert isinstance(group.key, int)
        assert isinstance(group.uuid, str)
        assert isinstance(group.name, str)
        assert isinstance(group.description, str)
        assert isinstance(group.device_type, str)
        assert isinstance(group.device_type_display, str)
        assert isinstance(group.device_class, str)
        assert isinstance(group.device_class_display, str)
        assert isinstance(group.is_enabled, bool)
        assert isinstance(group.resource_count, int)

        # UUID should be valid format
        if group.uuid:
            assert len(group.uuid) == 36  # UUID format: 8-4-4-4-12

        # Device type should be a known value
        assert (
            group.device_type in DEVICE_TYPE_MAP
            or group.device_type_display in DEVICE_TYPE_MAP.values()
        )

        # Device class should be a known value
        assert (
            group.device_class in DEVICE_CLASS_MAP
            or group.device_class_display in DEVICE_CLASS_MAP.values()
        )

    def test_resource_group_timestamps(self, live_client: VergeClient) -> None:
        """Test that resource group timestamps are valid."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]

        # created_at and modified_at may be None or datetime
        if group.created_at is not None:
            assert group.created_at.year >= 2020  # Sanity check

        if group.modified_at is not None:
            assert group.modified_at.year >= 2020  # Sanity check

            # modified_at should be >= created_at if both exist
            if group.created_at is not None:
                assert group.modified_at >= group.created_at

    def test_resource_group_repr(self, live_client: VergeClient) -> None:
        """Test resource group string representation."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        repr_str = repr(group)

        assert "ResourceGroup" in repr_str
        assert group.name in repr_str


@pytest.mark.integration
class TestResourceGroupIterationIntegration:
    """Integration tests for ResourceGroupManager iteration."""

    def test_iter_all_resource_groups(self, live_client: VergeClient) -> None:
        """Test iterating through all resource groups."""
        # Use iter_all with small page size to test pagination
        count = 0
        for group in live_client.resource_groups.iter_all(page_size=2):
            assert isinstance(group, ResourceGroup)
            count += 1

        # Count should match list() count
        all_groups = live_client.resource_groups.list()
        assert count == len(all_groups)

    def test_manager_iteration(self, live_client: VergeClient) -> None:
        """Test direct iteration over manager."""
        groups_from_iter = list(live_client.resource_groups)
        groups_from_list = live_client.resource_groups.list()

        assert len(groups_from_iter) == len(groups_from_list)
